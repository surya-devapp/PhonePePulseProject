# PhonePePlusProject

## Overview
This project analyzes and visualizes PhonePe Pulse data to uncover transaction, user, device, and insurance trends across India. It uses Python, MySQL, and Streamlit for data import, storage, and interactive dashboarding.

## Features
- Import and store PhonePe Pulse data (from https://github.com/PhonePe/pulse.git) into a MySQL database
- Analyze transaction dynamics, device dominance, insurance penetration, and user engagement
- Interactive Streamlit dashboard with Altair and bar charts

## Folder Structure
# PhonePePlusProject

## Overview
This repository contains tools to import, store, analyze, and visualize PhonePe Pulse data (open dataset) for India. The goal is to provide an end-to-end pipeline:

- Extract JSON data from the PhonePe Pulse repository
- Load it into a MySQL database (structured tables)
- Explore and visualize results in an interactive Streamlit dashboard

Tech stack: Python (pandas, mysql-connector), MySQL, Streamlit, Altair.

## What you'll find here

- `myenv/import_data.py` — ETL script: parses PhonePe JSON files and inserts records into MySQL tables
- `myenv/mainpage.py` — Streamlit dashboard to explore transactions, users, devices, and insurance
- `pulse/` — expected location of the cloned PhonePe Pulse dataset (not included in this repo)

## Quickstart

1. Clone the PhonePe Pulse data (if you haven't):

```powershell
git clone https://github.com/PhonePe/pulse.git d:\\PhonePePlusProject\\pulse
```

2. Create and activate a Python virtual environment (Windows PowerShell):

```powershell
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
pip install --upgrade pip
```

3. Install required Python packages:

```powershell
pip install pandas mysql-connector-python streamlit altair
```

4. Configure MySQL:

- Start your MySQL server and create a database (example name: `phoneplus`).
- Update the MySQL credentials in `myenv/import_data.py` and `myenv/mainpage.py` if needed.

```sql
CREATE DATABASE phoneplus;
```

5. (Optional) If you already ran the import and got "out of range" errors, run these ALTER statements in MySQL to convert problematic columns to BIGINT:

```sql
ALTER TABLE transactions MODIFY `count` BIGINT;
ALTER TABLE users MODIFY registered_users BIGINT;
ALTER TABLE users MODIFY app_opens BIGINT;
ALTER TABLE devices MODIFY registered_users BIGINT;
ALTER TABLE devices MODIFY app_opens BIGINT;
ALTER TABLE insurance MODIFY `count` BIGINT;
```

6. Import the data (this can take time depending on dataset size):

```powershell
python myenv\\import_data.py
```

7. Important: run the importer before starting the dashboard

Before launching the Streamlit app, make sure the database has been populated by `import_data.py`. The dashboard expects the tables and aggregated data to be present. If you start the dashboard before importing, many pages may show empty results or errors.

8. Run the Streamlit dashboard:

```powershell
streamlit run myenv\\mainpage.py
```

Open the URL shown by Streamlit (usually `http://localhost:8501`).

## File structure

```
PhonePePlusProject/
├─ myenv/
│  ├─ import_data.py      # ETL script (parse JSON -> MySQL)
│  └─ mainpage.py         # Streamlit dashboard
├─ pulse/                 # (git clone of PhonePe/pulse) - data source
└─ README.md
```

Additional files created in this repo:

- `requirements.txt` — lists Python packages required by the project.
- `myenv/db_migrate.sql` — optional SQL script with ALTER TABLE statements to convert INT columns to BIGINT if you encounter "out of range" errors during import.


## Troubleshooting & Tips

- "Out of range value for column 'count'" — convert `count` columns to `BIGINT` as shown above.
- Missing data paths — the Pulse repo layout may change. If an ETL step fails due to missing folders, check the `pulse/data` folder and adapt `PULSE_DATA_PATH` in `import_data.py`.
- Streamlit caching — the dashboard caches the DB connection using `@st.cache_resource` and avoids closing the cached connection between queries.
- If you add or change table schemas, either drop and recreate the tables or use `ALTER TABLE` to update column types.

## Development notes

- Keep ETL code (`import_data.py`) separate from the dashboard (`mainpage.py`).
- The dashboard uses Altair for richer interactive charts (install `altair`).

## Credits

- PhonePe Pulse (data): https://github.com/PhonePe/pulse
- Libraries: pandas, mysql-connector-python, Streamlit, Altair

---
If you'd like, I can also add a `requirements.txt` and small sample queries or screenshots to this README.