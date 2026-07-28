# Small Business ETL Pipeline
This project connects order information from a real-world small business (Sweet Racks and Smokin' Butts BBQ, LLC) into PowerBI for reporting. A Python script pulls order details off of the Square API, transforms the data into a uniform format, then appends the information into a hierarchical series of PostgreSQL tables that are locally hosted. The database is then directly connected to PowerBI Desktop for dashboard construction and data analytics. 
This project serves to quickly and accurately tackle questions for the business stakeholder, such as:
- What is the busiest part of the day? When do we need the most employees on the floor?
- How much of each product did we sell today? How much should we prepare for tomorrow?
- What trends are we noticing, and how can we prevent having too little or too much stock?

**Project Scope:** In the current state, this script only pulls away a few main data points: a main "order" object per transaction, a list of "line items" that were attached to that order, and "modification" objects which correlate to each of the line items in every order. The script currently only tracks sales and major inventory items.
## File Directory
`pipeline.py`: Main script for the pipeline. First, the script utilizes environment variables to access the Square API for the owner's profile. The Square database is queried in 500 row chunks in compliance with server regulations.

`item_catalog.py`:
## Square API Python Script --- Data Extraction
## PostgreSQL Connection --- Data Transformation and Storage
<img width="415" height="230" alt="bbq-pipeline-sql-tables" src="https://github.com/user-attachments/assets/094dc9f0-1837-46e3-ab58-03b4a7eb8b09" />

## Database to PowerBI --- Data Reporting
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

