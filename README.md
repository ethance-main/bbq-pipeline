<div align=center> <img width="467" height="316" alt="image" src="https://github.com/user-attachments/assets/ce1d09ca-31dc-41dc-b41b-5a574ac20e0f" />

# Small Business ETL Pipeline (Version 0.7) 
</div>

This project connects order information from a real-world small business (Sweet Racks and Smokin' Butts BBQ, LLC) into PowerBI for reporting. A Python script pulls order details off of the Square API, transforms the data into a uniform format, then appends the information into a hierarchical series of PostgreSQL tables that are locally hosted. The database is then directly connected to PowerBI Desktop for dashboard construction and data analytics. 
This project serves to quickly and accurately tackle questions for the business stakeholder, such as:
- What is the busiest part of the day? When do we need the most employees on the floor?
- How much of each product did we sell today? How much should we prepare for tomorrow?
- What trends are we noticing, and how can we prevent having too little or too much stock?

**Project Scope:** In the current state, this script only pulls away a few main data points: a primary "order" object per transaction, a list of "line items" that are attached to that order, and "modification" objects which correlate to each of the line items in every order. The script currently only tracks sales and major inventory ingredients (meats).

<div align=center>
<img width="627" height="326" alt="image" src="https://github.com/user-attachments/assets/5da8973c-3b9b-4e2c-b914-03590d4474b7" />
</div>
  
## File Directory 

`pipeline.py`: Main script for the pipeline. `run_pipeline(days_back=1)` acts as the main execution function, relying on several, smaller functions to simulate the different stages of the pipeline:
- `get_order(days_back=1)`: Connects and sends a SQL query to the Square API housing the small business' sales data. Outputs the Order data structure in a raw format.
- `transform_orders(raw_orders)`: This function takes in the raw Order data structure produced by the Square API and transforms it into 3 distinct pandas dataframes, preserving only data deemed potentially useful for the pipeline applications. Outputs the three pandas dataframes.
- `process_line_item(item_name, variation_name=None)`: Helper function used in the `tranform_orders()` process. Menu items are typically renamed or structured in unique ways, which still referring to the same item. For example, one order could have an item called "mac n cheese - large" while another could have an item called "mac n cheese" with variation "large". Both entries refer to the same menu item. To unify formatting, this function consults the `item_catalog.py` file, which streamlines variations into a consistent data structure.
- `load_to_postgres(order_df, item_df, modifiers_df)`: Utilizing a cursor and connection to a PostgreSQL database, inserts each row from the pandas dataframes into their respective SQL tables. Prints the number of objects merged into each table.

`item_catalog.py`: A catalog of item variations. Over time, the business has modified, updated, added, and removed various items from the menu. These changes can result in the same item having multiple names: "mac n cheese - small" and "sm. mac", for example. This lookup dictionary is utilized in the `process_line_item()` function in order to unify formatting and include meat amount and type for every menu item.

## Square API Python Script --- Data Extraction

<div align=center>
<img width="497" height="401" alt="image" src="https://github.com/user-attachments/assets/b95f4124-c2ac-48b5-a822-dee8c7f4bad6" />
</div>


Data Extraction from the Square API is controlled by the `pipeline.py` script defined in this repository. First, the script utilizes environment variables to access the Square API for the owner's profile. Queries have two limitations when contacting the API: limited to 500 rows, and within a 90 day window. Therefore, multiple, recursive queries are ran to capture every order within a particular time interval. The Order data object obtained from the API is then transformed into 3 distinct dataframes:
1. `order_df`: Contains overhead data for each transaction, including a unique order id, date and time the order was created/updated/closed, the location of sales, and various monetary amounts such as tip amount, total money, etc.
2. `items_df`: Each row corresponds to an individual line item, including a relationship to the unique order id, a unique item id, the quantity of items purchased, the base price of the item, the type of meat (and what amount) is used in the item, etc.
3. `modifiers_df`: Each row corresponds to a modification to a line item. One item can have multiple related modifications. Each row includes a unique id, related line item and order ids, modifier price and quantity, etc.

After the dataframes are constructed, the data is loaded into their respective database tables, and the script ends.

## PostgreSQL Connection --- Data Storage and Management
<div align=center>
<img width="400" height="250" alt="image" src="https://github.com/user-attachments/assets/95828ff9-1c9d-4678-81c0-f7c50ba30f5f"/>
</div>
The PostgreSQL database contains order history throughout the entire lifespan of the business, going back to 2020. Data is broken up into 3 distinct tables: order_records, line_item_records, and modifier_records. Each order can have multiple line items, each line item can have multiple (or zero) modifications. Following is the columns for each table:

- `order_records`: order_id, ticket_name, date_created, time_created, date_updated, time_updated, date_closed, time_closed, order_source, order_status, total_money, total_tax_money, total_tip_money, total_discount_money, total_service_charge_money, currency, location_id, order_version
  
- `line_item_records`: unique_id, order_id, item_name, catalog_object_id, item_quantity, item_base_price, item_tax_money, item_discount_money, item_total_money, item_size, item_meat, meat_amount, notes, item_category, item_subcategory
  
- `modifier_records`: mod_uid, item_uid, order_id, catalog_object_id, catalog_version, mod_name, quantity, base_price, total_price

## Database to PowerBI --- Data Reporting
The data from the PostgreSQL database has been loaded into PowerBI, however the dashboard still needs to be constructed. (TODO)

## Project Roadmap
- [X] Establish a PostgreSQL database, locally hosted
- [X] Write the Python script which uploads Square Orders to SQL database
- [X] Construct item catalog to unify item formatting, simplify menu variance
- [X] Connect the SQL database to PowerBI Desktop
- [ ] Construct a Weekly Sales Dashboard, comparing sales against previous week
- [ ] Automate the Python script to run on a regular, weekly schedule
- [ ] Move SQL database to an independent home server, rework database credentials
- [ ] Explore and expand into other reporting opportunities (Inventory, Expenses, Labor, etc.)

## Changelog
### Version 0.7 (First Public Release) - 7/27/2026
- Python script needs to be executed manually in order to refresh the PostgreSQL database
- PostgreSQL database is still hosted locally
- Data is loaded into PowerBI Desktop, dashboards still need to be constructed

