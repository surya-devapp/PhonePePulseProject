# PhonePe Pulse Insights Dashboard

## Overview
This project provides a comprehensive dashboard to analyze and visualize PhonePe Pulse data, uncovering trends in transactions, user registrations, device usage, and insurance penetration across India. It leverages a robust tech stack including **Python**, **MySQL**, **Streamlit**, and **Plotly** to deliver interactive and animated insights.

## Features
- **Data ETL**: Automated extraction of data from the PhonePe Pulse repository and loading into a structured MySQL database.
- **Interactive Dashboard**: A user-friendly Streamlit interface with navigation for different analysis modules.
- **Visualizations**: 
    - **Animated India Map**: Time-series visualization of state-level data.
    - **Transaction Dynamics**: Deep dive into transaction types and volumes.
    - **Device & User Analysis**: Insights into device preferences and user growth.
    - **Insurance Trends**: Analysis of the growing insurance sector on the platform.

## Folder Structure
```
PhonePePulseProject/
├─ Visualizations/          # Modules for specific analysis charts
│  ├─ case1.py              # Transaction dynamics
│  ├─ case2.py              # Device dominance
│  ├─ case3.py              # Transaction analysis
│  ├─ case4.py              # User registration
│  └─ case5.py              # Insurance engagement
├─ pulse-master/            # (Expected) Cloned PhonePe Pulse data source
├─ import_data.py           # ETL script to parse JSON and populate MySQL
├─ main_page.py             # Main Streamlit application entry point
├─ requirements.txt         # Project dependencies
└─ README.md                # Project documentation
```

## Prerequisites
1.  **Python 3.8+**: Ensure Python is installed.
2.  **MySQL Server**: You need a local or remote MySQL instance running.
3.  **PhonePe Pulse Data**: Clone the data repository.

## Installation & Setup

### 1. Clone the Repository
If you haven't already, clone the specific PhonePe Pulse data repository into the project folder so the ETL script can access it.
```powershell
git clone https://github.com/PhonePe/pulse.git pulse-master
```

### 2. Set Up Virtual Environment (Optional but Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

### 3. Install Dependencies
Install all required Python packages using `pip`:
```powershell
pip install -r requirements.txt
```

### 4. Database Configuration
1.  Open `main_page.py` and `import_data.py`.
2.  Update the MySQL connection details (`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_DB`) to match your local setup.
3.  Ensure the database (e.g., `project_data_base`) exists or let the script accept the credentials to create tables within it.

### 5. Data Import (ETL)
Before running the dashboard, you must populate the database:
```powershell
python import_data.py
```
*Note: This process may take some time as it processes a large volume of JSON files.*

## How to Run the App
Once the database is ready, launch the Streamlit dashboard:

```powershell
streamlit run main_page.py
```

Or, if you prefer using python module syntax:
```powershell
python -m streamlit run main_page.py
```

The application will open in your default web browser at `http://localhost:8501`.

## Troubleshooting
- **Database Errors**: Ensure your MySQL server is running and the credentials in the python files are correct.
- **Missing Data**: Verify that the `pulse-master` folder contains the `data` directory with the JSON files.
- **Dependency Issues**: Try running `pip install -r requirements.txt` again to ensure all packages are installed.
