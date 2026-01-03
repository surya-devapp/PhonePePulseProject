import pandas as pd
import streamlit as st
import plotly.express as px
import mysql.connector
import numpy as np
from outliers_detection import show_data_quality_summary

def plot_User_Registration_Analysis(connection):
    """
    User Registration Analysis Dashboard with comprehensive visualizations.
    Enhanced with IQR and Z-score outlier detection.
    """
    st.header('4. User Registration Analysis Dashboard')
    
    # --- DATA QUALITY SUMMARY (NEW - Outlier Detection) ---
    try:
        base_query_sample = "SELECT * FROM TOP_USER_RECORD LIMIT 1000;"
        df_sample = pd.read_sql(base_query_sample,connection)
        show_data_quality_summary(df_sample, "User Registration Data (Sample)")
    except Exception as e:
        st.warning(f"Could not load data quality summary: {e}")
    
    # 1. INITIAL DATA FETCH & GLOBAL FILTER SETUP
    
    # Fetch data for selectbox options only
    q_options = "SELECT DISTINCT YEAR, QUARTER, STATE FROM TOP_USER_RECORD;"
    df_options = pd.read_sql(q_options,connection)
    
    year_options = ["ALL"] + sorted(df_options['YEAR'].unique().tolist())
    quarter_options = ["ALL"] + sorted(df_options['QUARTER'].unique().tolist())

    # Create the Master Filters (used across Sections 1, 2, 3, and Pie Chart)
    col1, col2 = st.columns(2)
    with col1:
        master_year = st.selectbox('Select Year (Global Filter)', year_options, key='master_year')
    with col2:
        master_quarter = st.selectbox('Select Quarter (Global Filter)', quarter_options, key='master_quarter')

    # --- SECTION 1: TOP STATES ---
    st.subheader('1. Top User Registration Analysis Across States')

    # Dynamic SQL Query Construction for States
    base_query_state = """
        SELECT STATE, SUM(REGISTERED_USERS) AS total_users
        FROM TOP_USER_RECORD
    """
    where_clauses_state = []
    parameters_state = []

    if master_year != 'ALL':
        where_clauses_state.append("YEAR = %s")
        parameters_state.append(master_year)

    if master_quarter != 'ALL':
        where_clauses_state.append("QUARTER = %s")
        parameters_state.append(master_quarter)

    if where_clauses_state:
        base_query_state += " WHERE " + " AND ".join(where_clauses_state)

    base_query_state += """
        GROUP BY STATE
        ORDER BY total_users DESC
        LIMIT 10;
    """

    query_params_state = tuple(parameters_state) if parameters_state else None
    filter_states = pd.read_sql(base_query_state,connection, params=query_params_state)

    year_label = master_year if master_year != 'ALL' else 'All Years'
    quarter_label = f"Q{master_quarter}" if master_quarter != 'ALL' else 'All Quarters'
    title_str = f"Top 10 States by Registered Users, {year_label} {quarter_label}"

    fig1 = px.bar(filter_states, x="STATE", y="total_users", color='STATE', title=title_str)
    fig1.update_layout(xaxis_title="State", yaxis_title="Total Registered Users")
    st.plotly_chart(fig1)

    st.markdown("---")

    # --- SECTION 2 & 3: TOP DISTRICTS AND PINCODES ---
    
    def generate_top_entity_chart(entity_type, title_prefix, master_year, master_quarter):
        """Helper function to generate bar charts for Districts and Pincodes."""
        
        base_query = """
            SELECT ENTITY_NAME, SUM(REGISTERED_USERS) AS total_users
            FROM TOP_USER_RECORD
        """
        where_clauses = [f"ENTITY_TYPE = '{entity_type}'"]
        parameters = []

        if master_year != 'ALL':
            where_clauses.append("YEAR = %s")
            parameters.append(master_year)

        if master_quarter != 'ALL':
            where_clauses.append("QUARTER = %s")
            parameters.append(master_quarter)

        base_query += " WHERE " + " AND ".join(where_clauses)
        base_query += """
            GROUP BY ENTITY_NAME
            ORDER BY total_users DESC
            LIMIT 10;
        """

        query_params = tuple(parameters) if parameters else None
        df_entity = pd.read_sql(base_query,connection, params=query_params)

        year_label = master_year if master_year != 'ALL' else 'All Years'
        quarter_label = f"Q{master_quarter}" if master_quarter != 'ALL' else 'All Quarters'
        title_str = f"Top 10 {title_prefix}, {year_label} {quarter_label}"
        
        # Ensure Pincode is treated as a category (string) for correct plotting
        if entity_type == 'Pincode':
            df_entity["ENTITY_NAME"] = df_entity["ENTITY_NAME"].astype('str')

        fig = px.bar(df_entity, x="ENTITY_NAME", y="total_users", color='ENTITY_NAME', title=title_str)
        fig.update_layout(xaxis_title=title_prefix, yaxis_title="Total Registered Users")
        return fig
    
    st.subheader('2. Top Districts by Registered Users')
    fig2 = generate_top_entity_chart('District', 'Districts', master_year, master_quarter)
    st.plotly_chart(fig2)
    
    st.markdown("---")
    
    st.subheader('3. Top Pincodes by Registered Users')
    fig3 = generate_top_entity_chart('Pincode', 'Pincodes', master_year, master_quarter)
    fig3.update_xaxes(type='category')
    fig3.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>" +
                          "State: %{customdata[0]}<br>" +
                          "Total Users: %{y:,.0f}<br>" +
                          "<extra></extra>"
        )
    st.plotly_chart(fig3)
    
    st.markdown("---")

    # --- SECTION 4: QUARTERLY TRENDS (State Specific) ---
    st.subheader('4. Quarterly Registration Trends for a Selected State')

    # State selection for trend
    selected_state = st.selectbox('Select State for Trend Analysis', sorted(df_options["STATE"].unique()), key='trend_state_q4')

    # Year selection for trend
    selected_year = st.selectbox('Select Year for Trend Analysis', year_options, key='trend_year_q4')

    # Dynamic SQL Query Construction for Trends
    base_query_trend = """
        SELECT QUARTER, SUM(REGISTERED_USERS) AS total_users
        FROM TOP_USER_RECORD
    """
    where_clauses_trend = ["STATE = %s"]
    parameters_trend = [selected_state]

    if selected_year != 'ALL':
        where_clauses_trend.append("YEAR = %s")
        parameters_trend.append(selected_year)
        
    base_query_trend += " WHERE " + " AND ".join(where_clauses_trend)
    base_query_trend += """
        GROUP BY QUARTER
        ORDER BY QUARTER;
    """

    query_params_trend = tuple(parameters_trend)
    df_trend = pd.read_sql(base_query_trend,connection, params=query_params_trend)

    year_label_q4 = f"({selected_year})" if selected_year != 'ALL' else '(All Years Combined)'
    title_str_q4 = f"Quarterly User Trends for {selected_state} {year_label_q4}"

    fig4 = px.line(df_trend, x="QUARTER", y="total_users", markers=True, title=title_str_q4)
    fig4.update_xaxes(type='category')
    fig4.update_layout(xaxis_title="Quarter", yaxis_title="Total Registered Users")
    st.plotly_chart(fig4)

    st.markdown("---")

    # --- SECTION 5: DISTRICT SHARE (Pie Chart) ---
    st.subheader("5. Top 10 District Share in Total Registrations")
    
    base_query_pie = """
        SELECT ENTITY_NAME, SUM(REGISTERED_USERS) AS total_users
        FROM TOP_USER_RECORD
    """
    where_clauses_pie = ["ENTITY_TYPE = 'District'"]
    parameters_pie = []

    if master_year != 'ALL':
        where_clauses_pie.append("YEAR = %s")
        parameters_pie.append(master_year)

    if master_quarter != 'ALL':
        where_clauses_pie.append("QUARTER = %s")
        parameters_pie.append(master_quarter)

    base_query_pie += " WHERE " + " AND ".join(where_clauses_pie)
    base_query_pie += " GROUP BY ENTITY_NAME;"

    query_params_pie = tuple(parameters_pie) if parameters_pie else None
    df_share = pd.read_sql(base_query_pie,connection, params=query_params_pie).sort_values(by='total_users', ascending=False).head(10)
    
    year_label_pie = master_year if master_year != 'ALL' else 'All Years'
    quarter_label_pie = f"Q{master_quarter}" if master_quarter != 'ALL' else 'All Quarters'
    title_str_pie = f"Top 10 District Share, {year_label_pie} {quarter_label_pie}"

    fig5 = px.pie(df_share, names="ENTITY_NAME", values="total_users", title=title_str_pie)
    st.plotly_chart(fig5)
