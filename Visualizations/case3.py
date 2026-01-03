import pandas as pd
import streamlit as st
import plotly.express as px
import mysql.connector
import numpy as np
import plotly.graph_objects as go
from outliers_detection import show_data_quality_summary

def plot_Transaction_Analysis(connection):
    """
    Transaction Analysis Dashboard with comprehensive visualizations.
    Enhanced with IQR and Z-score outlier detection.
    """
    st.header('3. Top Transaction Analysis Dashboard')
    
    try:
        base_query_sample = "SELECT * FROM top_transaction_record LIMIT 1000;"
        df_sample = pd.read_sql(base_query_sample,connection)
        show_data_quality_summary(df_sample, "Top Transaction Data (Sample)")
    except Exception as e:
        st.warning(f"Could not load data quality summary: {e}")
    
    # 1. INITIAL DATA FETCH & GLOBAL FILTER SETUP
    
    # Fetch data for selectbox options only
    q_options = "SELECT DISTINCT YEAR, QUARTER, STATE FROM top_transaction_record;"
    try:
        df_options = pd.read_sql(q_options,connection)
    except Exception as e:
        st.error(f"Error connecting to database or querying options: {e}")
        return

    year_options = ["ALL"] + sorted(df_options['YEAR'].unique().tolist())
    quarter_options = ["ALL"] + sorted(df_options['QUARTER'].unique().tolist())

    st.markdown("### Global Filters")
    col1, col2 = st.columns(2)
    with col1:
        master_year = st.selectbox('Select Year', year_options, key='tx_master_year')
    with col2:
        master_quarter = st.selectbox('Select Quarter', quarter_options, key='tx_master_quarter')

    # Helper function for SQL and Plotly generation for Sections 1, 2, 3
    def generate_top_entity_chart(entity_level, entity_column, master_year, master_quarter):
        """Generates the SQL and Plotly figure for States, Districts, or Pincodes."""
        
        # Determine the base query structure
        if entity_level == 'State':
            select_entity = "STATE"
            group_by_entity = "STATE"
            where_entity = None
        else:
            select_entity = "ENTITY_NAME, STATE"
            group_by_entity = "ENTITY_NAME, STATE"
            where_entity = f"ENTITY_TYPE = '{entity_level}'"
        
        # 1. Dynamic SQL Query Construction
        base_query = f"""
            SELECT {select_entity}, 
                   SUM(TRANSACTION_COUNT) AS total_volume,
                   SUM(TRANSACTION_AMOUNT) AS total_value
            FROM top_transaction_record
        """
        where_clauses = []
        parameters = []

        if where_entity:
            where_clauses.append(where_entity)

        if master_year != 'ALL':
            where_clauses.append("YEAR = %s")
            parameters.append(master_year)

        if master_quarter != 'ALL':
            where_clauses.append("QUARTER = %s")
            parameters.append(master_quarter)

        if where_clauses:
            base_query += " WHERE " + " AND ".join(where_clauses)

        base_query += f"""
            GROUP BY {group_by_entity}
            ORDER BY total_volume DESC
            LIMIT 10;
        """

        query_params = tuple(parameters) if parameters else None
        df_entity = pd.read_sql(base_query,connection, params=query_params)

        # 2. Plotly Figure Generation (Dual-Axis Chart for Volume/Value)
        
        # Ensure Pincode is string for correct plotting
        if entity_level == 'Pincode':
            df_entity[entity_column] = df_entity[entity_column].astype('str')

        year_label = master_year if master_year != 'ALL' else 'All Years'
        quarter_label = f"Q{master_quarter}" if master_quarter != 'ALL' else 'All Quarters'
        title_str = f"Top 10 {entity_column} by Transaction Volume/Value, {year_label} {quarter_label}"

        # Create a combined Plotly figure with two traces
        fig = go.Figure()

        # Trace 1: Transaction Volume (Bar Chart, left y-axis)
        fig.add_trace(go.Bar(
            x=df_entity[entity_column],
            y=df_entity['total_volume'],
            name='Transaction Volume (Count)',
            marker_color='skyblue',
            hovertemplate="<b>%{x}</b><br>Volume: %{y:,.0f}<br>Value: %{customdata[0]:,.2f}<extra></extra>",
            customdata=df_entity[['total_value']].values
        ))

        # Trace 2: Transaction Value (Line Chart, right y-axis)
        fig.add_trace(go.Scatter(
            x=df_entity[entity_column],
            y=df_entity['total_value'],
            name='Transaction Value (INR)',
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='darkorange'),
            hovertemplate="<b>%{x}</b><br>Volume: %{customdata[0]:,.0f}<br>Value: %{y:,.2f}<extra></extra>",
            customdata=df_entity[['total_volume']].values
        ))
        
        # Update layout for dual Y-axis
        fig.update_layout(
            title=title_str,
            xaxis_title=entity_column,
            yaxis=dict(
                title='Transaction Volume (Count)',
                title_font=dict(color='skyblue'),
                tickfont=dict(color='skyblue')
            ),
            yaxis2=dict(
                title='Transaction Value (INR)',
                title_font=dict(color='darkorange'),
                tickfont=dict(color='darkorange'),
                overlaying='y',
                side='right',
                tickformat=',.2s'
            ),
            legend=dict(x=0.01, y=0.99),
            barmode='group'
        )
        
        return fig

    # --- SECTION 1: TOP STATES ---
    st.subheader('3a. Top States by Transaction Volume and Value')
    fig1 = generate_top_entity_chart('State', 'STATE', master_year, master_quarter)
    st.plotly_chart(fig1)

    st.markdown("---")
    
    # --- SECTION 2: TOP DISTRICTS ---
    st.subheader('3b. Top Districts by Transaction Volume and Value')
    fig2 = generate_top_entity_chart('District', 'ENTITY_NAME', master_year, master_quarter)
    st.plotly_chart(fig2)
    
    st.markdown("---")
    
    # --- SECTION 3: TOP PINCODES ---
    st.subheader('3c. Top Pincodes by Transaction Volume and Value')
    fig3 = generate_top_entity_chart('Pincode', 'ENTITY_NAME', master_year, master_quarter)
    fig3.update_xaxes(type='category')
    st.plotly_chart(fig3)
    
    st.markdown("---")

    # --- SECTION 4: QUARTERLY TRENDS (State Specific) ---
    st.subheader('3d. Quarterly Transaction Volume Trends for a Selected State')

    selected_state = st.selectbox('Select State for Trend Analysis', sorted(df_options["STATE"].unique()), key='tx_trend_state')
    selected_year = st.selectbox('Select Year for Trend Analysis', year_options, key='tx_trend_year')

    base_query_trend = """
        SELECT QUARTER, SUM(TRANSACTION_COUNT) AS total_volume
        FROM top_transaction_record
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
    title_str_q4 = f"Quarterly Transaction Volume Trends for {selected_state} {year_label_q4}"

    fig4 = px.line(
        df_trend, 
        x="QUARTER", 
        y="total_volume", 
        markers=True, 
        title=title_str_q4
    )
    fig4.update_traces(hovertemplate="Quarter: %{x}<br>Volume: %{y:,.0f}<extra></extra>")
    fig4.update_xaxes(type='category')
    fig4.update_layout(xaxis_title="Quarter", yaxis_title="Total Transaction Volume (Count)")
    st.plotly_chart(fig4)

    st.markdown("---")

    # --- SECTION 5: DISTRICT SHARE (Pie Chart by Value) ---
    st.subheader("3e. Top 10 District Share in Total Transaction Value")
    
    base_query_pie = """
        SELECT ENTITY_NAME, SUM(TRANSACTION_AMOUNT) AS total_value
        FROM top_transaction_record
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
    df_share = pd.read_sql(base_query_pie,connection, params=query_params_pie).sort_values(by='total_value', ascending=False).head(10)
    
    year_label_pie = master_year if master_year != 'ALL' else 'All Years'
    quarter_label_pie = f"Q{master_quarter}" if master_quarter != 'ALL' else 'All Quarters'
    title_str_pie = f"Top 10 District Share (by Value), {year_label_pie} {quarter_label_pie}"

    fig5 = px.pie(
        df_share, 
        names="ENTITY_NAME", 
        values="total_value", 
        title=title_str_pie,
        hover_name="ENTITY_NAME",
        hover_data={"ENTITY_NAME": False, "total_value": True}
    )
    fig5.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                      "Total Value: ₹%{value:,.2f}<br>" +
                      "Share: %{percent}<extra></extra>"
    )
    st.plotly_chart(fig5)
