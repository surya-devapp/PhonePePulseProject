import mysql.connector
import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import numpy as np # For potential data manipulation like percentage calculations
from Visualizations.case1 import plot_transaction_dynamics 
from Visualizations.case2 import plot_device_dominance
from Visualizations.case5 import plot_insurance_engagement
from Visualizations.case4 import plot_User_Registration_Analysis
from Visualizations.case3 import plot_Transaction_Analysis

# --- Configuration ---
# Use a specific SQLite DB file. For MySQL, replace this with your connection details.
# MySQL connection details
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'Surya@123'
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_DB = 'project_data_base'

def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        port=MYSQL_PORT
    )

def plot_india_map_animated():
    """
    Animated map showing changes over quarters with top filters and Andaman fix.
    """
    
    st.header("🗺️ Animated India Map - Time Series")
    
    # --- FILTERS ON TOP (NOT SIDEBAR) ---
    st.markdown("### 🎛️ Select Analysis Parameters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Analysis Type
    with col1:
        datatype = st.selectbox(
            "Analysis Type",
            ["Transaction", "User", "Insurance"],
            key="map_analysis_type"
        )
    
    # Fetch available years and quarters
    basequery = f"""
        SELECT DISTINCT YEAR, QUARTER
        FROM aggregated_{datatype}_record
        ORDER BY YEAR, QUARTER
    """
    base_df = pd.read_sql(basequery, get_db_connection())
    
    # Year and Quarter filters
    with col2:
        selectedyear = st.selectbox(
            "Start Year",
            sorted(base_df["YEAR"].unique().astype(int).tolist()),
            key="map_year"
        )
    
    with col3:
        selectedquarter = st.selectbox(
            "Start Quarter",
            sorted(base_df["QUARTER"].unique().astype(int).tolist()),
            key="map_quarter"
        )
    
    # Color scheme selector
    with col4:
        color_scheme = st.selectbox(
            "Color Scheme",
            ["Sunset", "Turbo", "Viridis", "Plasma", "Inferno", "RdYlGn"],
            key="map_color_scheme"
        )
    
    st.info("💡 Click the play button below to watch the animation over time")
    st.markdown("---")
    
    # --- STATE NAME MAPPING (FIX ANDAMAN) ---
    def get_state_mapping():
        """Map database state names to GeoJSON names"""
        return {
            'Andaman & Nicobar Islands': 'Andaman & Nicobar',
            'Andaman and Nicobar Islands': 'Andaman & Nicobar',
            'Dadra & Nagar Haveli & Daman & Diu': 'Dadra and Nagar Haveli and Daman and Diu',
            'Orissa': 'Odisha',
        }
    
    # --- FETCH DATA ---
    query = """
        SELECT 
            STATE,
            YEAR,
            QUARTER,
            CONCAT(YEAR, '-Q', QUARTER) AS period,"""
    
    if datatype == "Transaction":
        query += f"""
            SUM(transaction_amount) AS total_amount,
            SUM(TRANSACTION_COUNT) AS total_count
        FROM aggregated_{datatype}_record
        WHERE YEAR >= {selectedyear} AND QUARTER >= {selectedquarter}
        GROUP BY STATE, YEAR, QUARTER
        ORDER BY YEAR, QUARTER
        """
    elif datatype == "User":
        query += f"""
            SUM(Device_Count) AS total_users,
            MAX(APPS_OPEN) AS apps_open_count
        FROM aggregated_{datatype}_record
        WHERE YEAR >= {selectedyear} AND QUARTER >= {selectedquarter}
        GROUP BY STATE, YEAR, QUARTER
        ORDER BY YEAR, QUARTER
        """
    elif datatype == "Insurance":
        query += f"""
            SUM(insurance_amount) AS total_amount,
            SUM(insurance_COUNT) AS total_count
        FROM aggregated_{datatype}_record
        WHERE YEAR >= {selectedyear} AND QUARTER >= {selectedquarter}
        GROUP BY STATE, YEAR, QUARTER
        ORDER BY YEAR, QUARTER
        """
    
    try:
        df = pd.read_sql(query, get_db_connection())
        
        if df.empty:
            st.warning("No data available for selected filters.")
            return
        
        # ✅ FIX: Apply state name mapping to match GeoJSON
        state_mapping = get_state_mapping()
        df['STATE'] = df['STATE'].replace(state_mapping)
        
        # Rename columns for display
        if datatype != "User":
            df = df.rename(columns={
                'total_amount': 'Transaction Amount',
                'total_count': 'Total Transactions'
            })
            color_col = 'Transaction Amount'
            hover_dict = {
                'STATE': False,
                'Transaction Amount': ':,.2f',
                'Total Transactions': ':,.0f'
            }
        else:
            df = df.rename(columns={
                'total_users': 'Registered Users',
                'apps_open_count': 'Apps Opened'
            })
            color_col = 'Registered Users'
            hover_dict = {
                'STATE': False,
                'Registered Users': ':,.0f',
                'Apps Opened': ':,.0f'
            }
        
        # --- CREATE ANIMATED CHOROPLETH (FULL WIDTH) ---
        fig = px.choropleth(
            df,
            geojson="https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson",
            featureidkey='properties.ST_NM',
            locations='STATE',  # Now uses mapped names!
            color=color_col,
            animation_frame='period',
            animation_group='STATE',
            color_continuous_scale=color_scheme,
            hover_name='STATE',
            hover_data=hover_dict,
            title=f'<b>{datatype} Evolution Over Time</b><br>Starting from {selectedyear} Q{selectedquarter}'
        )
        
        # --- FULL PAGE LAYOUT ---
        fig.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor='rgba(240, 245, 250, 1)'
        )
        
        fig.update_layout(
            height=800,  # Taller for full page
            margin={"r":0, "t":80, "l":0, "b":0},
            
            # Title styling
            title_font_size=24,
            title_font_color='#2c3e50',
            title_x=0.5,
            title_xanchor='center',
            
            # Background
            paper_bgcolor='rgba(255, 255, 255, 1)',
            plot_bgcolor='rgba(255, 255, 255, 1)',
            
            # Font
            font=dict(
                family="Arial, sans-serif",
                size=14,
                color='#2c3e50'
            ),
            
            # Hover styling
            hoverlabel=dict(
                bgcolor="white",
                font_size=14,
                font_family="Arial",
                font_color='#2c3e50',
                bordercolor='#5f00ba'
            ),
            
            # Color bar styling
            coloraxis_colorbar=dict(
                title=color_col,
                thickness=20,
                len=0.7,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='#bdc3c7',
                borderwidth=2,
                tickfont=dict(color='#2c3e50', size=12)
            )
        )
        
        # --- ANIMATION CONTROLS ---
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1000
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 500
        
        # Update slider
        fig.layout.sliders[0].currentvalue.prefix = "Period: "
        fig.layout.sliders[0].currentvalue.font.size = 16
        fig.layout.sliders[0].currentvalue.font.color = '#2c3e50'
        fig.layout.sliders[0].font.color = '#2c3e50'
        
        # Display map (full width)
        st.plotly_chart(fig, use_container_width=True)
        
        # --- STATISTICS BELOW MAP ---
        st.markdown("---")
        st.markdown("### 📊 Animation Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_periods = df['period'].nunique()
        total_states = df['STATE'].nunique()
        
        with col1:
            st.metric("Total Periods", total_periods, help="Number of time frames")
        
        with col2:
            st.metric("States Tracked", total_states, help="Number of states")
        
        with col3:
            if datatype != "User":
                max_val = df['Transaction Amount'].max()
                st.metric("Peak Value", f"₹{max_val:,.0f}")
            else:
                max_val = df['Registered Users'].max()
                st.metric("Peak Users", f"{max_val:,.0f}")
        
        with col4:
            if datatype != "User":
                total_val = df.groupby('STATE')['Transaction Amount'].sum().sum()
                st.metric("Total", f"₹{total_val:,.0f}")
            else:
                total_val = df.groupby('STATE')['Registered Users'].sum().sum()
                st.metric("Total Users", f"{total_val:,.0f}")
        
        # --- TOP STATES IN LATEST PERIOD ---
        st.markdown("---")
        st.markdown("### 🏆 Top 5 States (Latest Period)")
        
        latest_period = df['period'].max()
        df_latest = df[df['period'] == latest_period].copy()
        
        if not df_latest.empty:
            top_5 = df_latest.nlargest(5, color_col)[['STATE', color_col]].reset_index(drop=True)
            top_5.index = top_5.index + 1
            
            st.dataframe(top_5, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error creating animated map: {e}")
        st.exception(e)
def main():
    st.set_page_config(layout="wide", page_title="PhonePe Insights Dashboard")

    st.title("PhonePe Transaction Insights & Analytics")
    st.sidebar.title("Navigation")
    analysis_options = {
        "Home Page" : plot_india_map_animated,
        "Decoding Transaction Dynamics": lambda : plot_transaction_dynamics(get_db_connection()),
        "Device Dominance & User Engagement": lambda : plot_device_dominance(get_db_connection()),
        "Top States Transaction Analysis" : lambda : plot_Transaction_Analysis(get_db_connection()), 
        "User Registration Analysis" : lambda : plot_User_Registration_Analysis(get_db_connection()),
        "Insurance Penetration & Growth": lambda : plot_insurance_engagement(get_db_connection()),
    }

    selected_analysis = st.sidebar.radio("Choose Analysis:", list(analysis_options.keys()))

    # Display the selected analysis
    analysis_options[selected_analysis]()

    st.sidebar.markdown("---")
    st.sidebar.info("Developed for PhonePe Transaction Insights Project.")


if __name__ == "__main__":
    main()