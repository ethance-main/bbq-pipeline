from square import Square
from square.environment import SquareEnvironment
from item_catalog import ITEM_CATALOG
import psycopg2
import pandas as pd
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
# load environment variables from .env file
load_dotenv()

# Initialize Square client
client = Square(
    token=os.environ.get("SQUARE_ACCESS_TOKEN"),
    environment=SquareEnvironment.PRODUCTION
)
# Initialize PostgreSQL connection
conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    database=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"]
)
# Create a cursor for executing SQL commands
cursor = conn.cursor()

# Convert Square's ISO 8601 timestamp to EST datetime object
def convert_to_est(timestamp_str):
    if not timestamp_str:
        return None
    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    est_dt = dt.astimezone(ZoneInfo("America/New_York"))
    return est_dt.replace(microsecond=0, tzinfo=None)  # Remove microseconds for cleaner output

"""
PIPELINE STAGE 1: Fetch Orders
Requires: Square API access token, location IDs, and date range (days_back)
Modifies: None
Effects: Fetches orders from Square API and returns a list of order objects
"""
def get_orders(days_back=1):
    all_orders = []
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)
    # Fetch orders in chunks of 89 days to avoid API limitations
    chunk_days = 89
    current_start = start_time
    while current_start < end_time:
        current_end = min(current_start + timedelta(days=chunk_days), end_time)
        cursor = None
        while True:
            try:
                query_body = {
                    "location_ids": [os.environ.get("LOCATION_ID_1"), os.environ.get("LOCATION_ID_2"),
                                    os.environ.get("LOCATION_ID_3"), os.environ.get("LOCATION_ID_4")],
                                    # Add more location IDs as needed
                    # Set a limit for the number of orders to fetch per request
                    "limit": 500,
                    "query": {
                        "filter": {
                            "date_time_filter": {
                                "created_at": {
                                    "start_at": current_start.isoformat(),
                                    "end_at": current_end.isoformat()
                                }
                            }
                        },
                        "sort": {
                            "sort_field": "CREATED_AT",
                            "sort_order": "ASC"
                        }
                    }
                }
                # If a cursor is present, include it in the request to fetch the next page of results
                if cursor:
                    query_body["cursor"] = cursor
                response = client.orders.search(
                    location_ids=query_body["location_ids"],
                    limit=query_body["limit"],
                    cursor=query_body.get("cursor"),
                    query=query_body["query"]
                )
                chunk = response.orders if hasattr(response, 'orders') else []
                # Add the fetched chunk of orders to the overall list
                all_orders.extend(chunk)
                print(f"Fetched {len(chunk)} orders from {current_start.date()} to {current_end.date()}. Total so far: {len(all_orders)}")
                cursor = response.cursor if hasattr(response, 'cursor') else None
                if not cursor:
                    break
            except Exception as e:
                print(f"Error fetching orders from {current_start.date()} to {current_end.date()}: {e}")
                break
        current_start = current_end
    print(f"Total orders fetched: {len(all_orders)}")
    return all_orders

"""
Helper function to process line items and map them to the item catalog. 
If the item or its variation is not found, it returns a default structure with "None" values.
"""
def process_line_item(item_name, variation_name=None):
    if item_name in ITEM_CATALOG:
        return ITEM_CATALOG[item_name]
    if variation_name:
        combined_name = f"{item_name} - {variation_name}"
        if combined_name in ITEM_CATALOG:
            return ITEM_CATALOG[combined_name]
    print(f"Item '{item_name}' with variation '{variation_name}' not found in catalog.")
    return {
        "base_name":    item_name,
        "meat_type":    "None",
        "size":         "None",
        "meat_amount":  0,
        "category":     "None",
        "subcategory":  "None"
    }

"""
PIPELINE STAGE 2: Transform Orders
Requires: List of order objects fetched from Square API
Modifies: None
Effects: Transforms the raw order data into structured DataFrames for orders, items, and modifiers
"""
def transform_orders(raw_orders):
    order_records = []
    item_records = []
    modifier_records = []
    for o in raw_orders:
        order_id = o.id if o.id else None
        ticket_name = o.ticket_name if o.ticket_name else None
        created_at = convert_to_est(o.created_at) if o.created_at else None
        updated_at = convert_to_est(o.updated_at) if o.updated_at else None
        complete_at = convert_to_est(o.closed_at) if o.closed_at else None
        source = (o.source.name if hasattr(o.source, 'name') else str(o.source)) if o.source else None
        total_money = o.total_money.amount if o.total_money else 0
        total_tax_money = o.total_tax_money.amount if o.total_tax_money else 0
        total_tip_money = o.total_tip_money.amount if o.total_tip_money else 0
        total_discount_money = o.total_discount_money.amount if o.total_discount_money else 0
        service_charge_money = o.total_service_charge_money.amount if o.total_service_charge_money else 0
        currency = o.total_money.currency if o.total_money else None
        location_id = o.location_id if o.location_id else None
        order_version = o.version if o.version else None

        order_records.append({
            "order_id": order_id,
            "ticket_name": ticket_name,
            "date_created": created_at.date() if created_at else None,
            "time_created": created_at.time() if created_at else None,
            "date_updated": updated_at.date() if updated_at else None,
            "time_updated": updated_at.time() if updated_at else None,
            "date_closed": complete_at.date() if complete_at else None,
            "time_closed": complete_at.time() if complete_at else None,
            "order_source": source,
            "order_status": o.state if o.state else None,
            "total_money": (total_money / 100),
            "total_tax_money": (total_tax_money / 100),
            "total_tip_money": (total_tip_money / 100),
            "total_discount_money": (total_discount_money / 100),
            "total_service_charge_money": (service_charge_money / 100),
            "currency": currency,
            "location_id": location_id,
            "version": order_version
        })
        if o.line_items:
            for line_item in o.line_items:
                parsed_item = process_line_item((line_item.name).lower() if line_item.name else None, (line_item.variation_name).lower() if line_item.variation_name else None)
                item_records.append({
                    "unique_id": line_item.uid,
                    "order_id": order_id,
                    "item_name": parsed_item["base_name"],
                    "catalog_object_id": line_item.catalog_object_id if line_item.catalog_object_id else None,
                    "item_quantity": line_item.quantity if line_item.quantity else None,
                    "item_base_price": (line_item.base_price_money.amount / 100) if line_item.base_price_money else 0,
                    "item_tax_money": (line_item.total_tax_money.amount / 100) if line_item.total_tax_money else 0,
                    "item_discount_money": (line_item.total_discount_money.amount / 100) if line_item.total_discount_money else 0,
                    "item_total_money": (line_item.total_money.amount / 100) if line_item.total_money else 0,
                    "item_size": parsed_item["size"],
                    "item_meat": parsed_item["meat_type"],
                    "meat_weight_lbs": parsed_item["meat_amount"],
                    "notes": line_item.note if line_item.note else None,
                    "item_category": parsed_item["category"],
                    "item_subcategory": parsed_item["subcategory"]
                })
                if line_item.modifiers:
                    for modifier in line_item.modifiers:
                        modifier_records.append({
                            "mod_uid": modifier.uid,
                            "item_uid": line_item.uid,
                            "order_id": order_id,
                            "modifier_name": modifier.name if modifier.name else None,
                            "catalog_object_id": modifier.catalog_object_id if modifier.catalog_object_id else None,
                            "catalog_version": modifier.catalog_version if modifier.catalog_version else None,
                            "modifier_quantity": modifier.quantity if modifier.quantity else None,
                            "modifier_base_price": (modifier.base_price_money.amount / 100) if modifier.base_price_money else 0,
                            "modifier_total_money": (modifier.total_price_money.amount / 100) if modifier.total_price_money else 0
                        })
    orders_df = pd.DataFrame(order_records)
    items_df = pd.DataFrame(item_records)
    modifiers_df = pd.DataFrame(modifier_records)
    return (orders_df, items_df, modifiers_df)

"""
PIPELINE STAGE 3: Load to PostgreSQL
Requires: DataFrames for orders, items, and modifiers
Modifies: PostgreSQL database tables for orders, items, and modifiers
Effects: Inserts the transformed data into the respective PostgreSQL tables, handling conflicts by ignoring duplicates
"""
def load_to_postgres(orders_df, items_df, modifiers_df):
    # Load orders
    for _, row in orders_df.iterrows():
        cursor.execute(f"""
            INSERT INTO {os.environ.get("DB_ORDERS_TABLE")} (
                order_id, ticket_name, date_created, time_created, date_updated,
                time_updated, date_closed, time_closed, order_source, order_status,
                total_money, total_tax_money, total_tip_money, total_discount_money,
                total_service_charge_money, currency, location_id, order_version
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            ) ON CONFLICT (order_id) DO NOTHING;
        """, tuple(row))
    # Load items
    for _, row in items_df.iterrows():
        cursor.execute(f"""
            INSERT INTO {os.environ.get("DB_ITEMS_TABLE")} (
                unique_id, order_id, item_name, catalog_object_id,
                item_quantity, item_base_price, item_tax_money, item_discount_money,
                item_total_money, item_size, item_meat, meat_amount,
                notes, item_category, item_subcategory
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            ) ON CONFLICT (unique_id) DO NOTHING;
        """, tuple(row))
    # Load modifiers
    for _, row in modifiers_df.iterrows():
        cursor.execute(f"""
            INSERT INTO {os.environ.get("DB_MODIFIER_TABLE")} (
                mod_uid, item_uid, order_id, catalog_object_id,
                catalog_version, mod_name, quantity, base_price,
                total_price
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s
            ) ON CONFLICT (mod_uid) DO NOTHING;
        """, tuple(row))
    # Commit the transaction to save changes to the database
    conn.commit()
    print(f"Merged {len(orders_df)} orders into PostgreSQL table.")
    print(f"Merged {len(items_df)} items into PostgreSQL table.")
    print(f"Merged {len(modifiers_df)} modifications into PostgreSQL table.")

"""
PIPELINE EXECUTION
This function orchestrates the entire ETL pipeline by fetching orders, transforming them into structured DataFrames
"""
def run_pipeline(days_back=1):
    orders = get_orders(days_back)
    if not orders:
        print("No orders fetched. Exiting pipeline.")
        return
    orders_df, items_df, modifiers_df = transform_orders(orders)
    if orders_df.empty:
        print("No records to load after transformation. Exiting pipeline.")
        return
    load_to_postgres(orders_df, items_df, modifiers_df)

run_pipeline(days_back=7)