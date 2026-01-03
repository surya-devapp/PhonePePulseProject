import pandas as pd
import streamlit as st
import plotly.express as px
import mysql.connector
import numpy as np
from outliers_detection import show_data_quality_summary


def plot_transaction_dynamics(connection):
    """
    Analyzes transaction dynamics by querying the aggregated_transaction_record table
    based on dynamic Streamlit filters (State, Year).
    Enhanced with IQR and Z-score outlier detection.
    """
    st.header("1. Decoding Transaction Dynamics on PhonePe")
    st.write("Analyze transaction trends across states, quarters, and payment categories.")
    
    # --- DATA QUALITY SUMMARY (NEW - Outlier Detection) ---
    try:
        base_query_sample = "SELECT * FROM aggregated_transaction_record;"
        df_sample = pd.read_sql(base_query_sample, connection)
        show_data_quality_summary(df_sample, "Transaction Data (Sample)")
    except Exception as e:
        st.warning(f"Could not load data quality summary: {e}")
    
    # --- 1. INITIAL SETUP & GLOBAL FILTERS ---
    
    # Fetch initial options for selectboxes
    q_options = "SELECT DISTINCT STATE, YEAR, TRANSACTION_TYPE FROM aggregated_transaction_record;"
    try:
        df_options = pd.read_sql(q_options, connection)
    except Exception as e:
        st.error(f"Error connecting to database or querying options: {e}")
        return

    if df_options.empty:
        st.warning("No transaction data available to plot.")
        return

    # Setup Filter Options
    state_options = ['All'] + sorted(df_options['STATE'].unique().tolist())
    year_options = ['All'] + sorted(df_options['YEAR'].unique().tolist())
    
    col1, col2 = st.columns(2)
    with col1:
        selected_state = st.selectbox("Select State (Global)", state_options, key='tx_state_global')
    with col2:
        selected_year = st.selectbox("Select Year (Global)", year_options, key='tx_year_global')

    # Construct Title Suffixes
    year_suffix = selected_year if selected_year != 'All' else 'All Years'
    state_suffix = selected_state if selected_state != 'All' else 'All States'
    filter_label = f" in {state_suffix}, {year_suffix}"

    # --- 2. DYNAMIC SQL QUERY (Foundation for Plots 1, 2, 4, 5) ---
    
    base_query = """
        SELECT YEAR, QUARTER, TRANSACTION_TYPE, 
               SUM(TRANSACTION_COUNT) AS total_count,
               SUM(transaction_amount) AS total_amount
        FROM aggregated_transaction_record
    """
    where_clauses = []
    parameters = []

    if selected_state != 'All':
        where_clauses.append("STATE = %s")
        parameters.append(selected_state)

    if selected_year != 'All':
        where_clauses.append("YEAR = %s")
        parameters.append(selected_year)
    
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
    
    base_query += " GROUP BY YEAR, QUARTER, TRANSACTION_TYPE ORDER BY YEAR, QUARTER, TRANSACTION_TYPE;"
    query_params = tuple(parameters) if parameters else None

    try:
        df_aggregated = pd.read_sql(base_query, connection, params=query_params)
    except Exception as e:
        st.error(f"Error executing aggregated query: {e}")
        return

    if df_aggregated.empty:
        st.info("No data for the selected filters.")
        return
    
    # Pre-calculate period for line charts
    df_aggregated['period'] = df_aggregated['YEAR'].astype(str) + ' Q' + df_aggregated['QUARTER'].astype(str)

    st.subheader("1a. Total Transaction Amount and Count Over Time")
    
    df_time_series = df_aggregated.groupby('period').agg(
        total_amount=('total_amount', 'sum'),
        total_count=('total_count', 'sum')
    ).reset_index().sort_values('period')

    fig_time = px.line(df_time_series, x='period', y='total_amount', markers=True,
                       title=f'Total Transaction Amount Over Time{filter_label}',
                       labels={'total_amount': 'Total Amount (INR)', 'period': 'Year-Quarter'})
    fig_time.update_traces(hovertemplate="<b>%{x}</b><br>Amount: ₹%{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_time, use_container_width=True)

    fig_timee = px.line(df_time_series, x='period', y='total_count', markers=True,
                        title=f'Total Transaction Count Over Time{filter_label}',
                        labels={'total_count': 'Total Transaction Count', 'period': 'Year-Quarter'})
    fig_timee.update_traces(hovertemplate="<b>%{x}</b><br>Count: %{y:,.0f}<extra></extra>")
    st.plotly_chart(fig_timee, use_container_width=True)

    st.markdown("---")

    st.subheader("1b. Overall Transaction Distribution by Type")
    
    df_type_agg = df_aggregated.groupby('TRANSACTION_TYPE').agg(
        total_amount=('total_amount', 'sum'),
        total_count=('total_count', 'sum')
    ).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Transaction Amount Distribution")
        amount_pie = px.pie(df_type_agg, values='total_amount', names='TRANSACTION_TYPE',
                            title='By Amount', hole=0.3)
        amount_pie.update_traces(hovertemplate="<b>%{label}</b><br>Amount: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>")
        st.plotly_chart(amount_pie, use_container_width=True)
    with col2:
        st.caption("Transaction Count Distribution")
        count_pie = px.pie(df_type_agg, values='total_count', names='TRANSACTION_TYPE',
                            title='By Count', hole=0.3)
        count_pie.update_traces(hovertemplate="<b>%{label}</b><br>Count: %{value:,.0f}<br>Share: %{percent}<extra></extra>")
        st.plotly_chart(count_pie, use_container_width=True)
            
    st.markdown("---")

    st.subheader("1c. State-wise Breakdown of a Selected Transaction Type")
    
    type_options = sorted(df_options['TRANSACTION_TYPE'].unique().tolist())
    selected_type_breakdown = st.selectbox("Select Transaction Type to Analyze", type_options, key='type_breakdown_select')
    
    # Dynamic SQL Query for State Breakdown
    base_query_state = """
        SELECT STATE, 
               SUM(transaction_amount) AS total_amount
        FROM aggregated_transaction_record
        WHERE TRANSACTION_TYPE = %s
    """
    parameters_state = [selected_type_breakdown]
    
    if selected_year != 'All':
        base_query_state += " AND YEAR = %s"
        parameters_state.append(selected_year)
    
    base_query_state += " GROUP BY STATE ORDER BY total_amount DESC LIMIT 20;"

    df_top_type_by_state = pd.read_sql(base_query_state, connection, params=tuple(parameters_state))

    if not df_top_type_by_state.empty:
        fig_top_type_state = px.bar(
            df_top_type_by_state, x='STATE', y='total_amount',
            title=f'Top 20 States for {selected_type_breakdown} Transactions ({year_suffix})',
            labels={'total_amount': 'Total Amount (INR)', 'STATE': 'State'},
            color='STATE', color_discrete_sequence=px.colors.qualitative.Vivid
        )
        fig_top_type_state.update_traces(hovertemplate="<b>%{x}</b><br>Amount: ₹%{y:,.2f}<extra></extra>")
        st.plotly_chart(fig_top_type_state, use_container_width=True)
    else:
        st.info(f"No data for '{selected_type_breakdown}' for the selected filters across states.")
    
    st.markdown("---")

    st.subheader("1d. Average Transaction Value per Type (Robust Median)")
    st.info("The Median is used as the robust average value to ignore high-value outliers.")
    
    df_avg_value = df_type_agg.copy()
    
    # Calculate Average Transaction Value (Amount/Count)
    df_avg_value['calculated_avg_value'] = np.where(
        df_avg_value['total_count'] > 0,
        df_avg_value['total_amount'] / df_avg_value['total_count'],
        0
    )
    
    # Robust Calculation (Median)
    median_avg_value = df_avg_value['calculated_avg_value'].median()
    
    df_avg_value = df_avg_value.sort_values('calculated_avg_value', ascending=False).round(2)

    fig_avg_value = px.bar(df_avg_value, x='TRANSACTION_TYPE', y='calculated_avg_value',
                        title=f'Average Transaction Value by Type{filter_label}',
                        labels={'calculated_avg_value': 'Avg Value (Amount/Count, INR)', 'TRANSACTION_TYPE': 'Transaction Type'},
                        color='TRANSACTION_TYPE', color_discrete_sequence=px.colors.qualitative.Pastel)
    
    # Add horizontal line for median
    fig_avg_value.add_hline(y=median_avg_value, line_dash="dash", line_color="gray", 
                            annotation_text=f"Robust Median Avg: ₹{median_avg_value:,.2f}")

    fig_avg_value.update_traces(hovertemplate="<b>%{x}</b><br>Avg Value: ₹%{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_avg_value, use_container_width=True)
        
    st.markdown("---")
    
    st.subheader("1e. Quarterly Trend Comparison Across All Types (Amount)")
    
    df_trend_comparison = df_aggregated.groupby(['period', 'TRANSACTION_TYPE'])['total_amount'].sum().reset_index()
    
    fig_qtr_comparison = px.line(df_trend_comparison, x='period', y='total_amount', color='TRANSACTION_TYPE',
                                title=f'Transaction Amount Trend by Type (Quarterly){filter_label}',
                                labels={'total_amount': 'Total Amount (INR)', 'period': 'Year-Quarter'},
                                line_group='TRANSACTION_TYPE', markers=True,
                                hover_data={'TRANSACTION_TYPE': True, 'total_amount': True, 'period': False})
    
    fig_qtr_comparison.update_traces(hovertemplate="<b>%{data.name}</b><br>Period: %{x}<br>Amount: ₹%{y:,.2f}<extra></extra>")
    fig_qtr_comparison.update_layout(legend_title_text='Transaction Type')
    st.plotly_chart(fig_qtr_comparison, use_container_width=True)
