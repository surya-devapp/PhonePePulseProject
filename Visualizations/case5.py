import pandas as pd
import streamlit as st
import plotly.express as px
import mysql.connector
import numpy as np
import plotly.graph_objects as go
from outliers_detection import show_data_quality_summary

def plot_insurance_engagement(connection):
    """
    Performs EDA on insurance transactions across states and districts using the 
    'aggregated_insurance_record' schema to analyze uptake, value, and market demand.
    Enhanced with IQR and Z-score outlier detection.
    """
    st.header("5. Insurance Engagement Analysis")
    st.write("**Scenario Goal:** Analyze insurance transaction volume and value across regions to understand market demand and growth potential.")
    
    # --- DATA QUALITY SUMMARY (NEW - Outlier Detection) ---
    try:
        base_query_sample = "SELECT * FROM aggregated_insurance_record LIMIT 1000;"
        df_sample = pd.read_sql(base_query_sample,connection)
        show_data_quality_summary(df_sample, "Insurance Data (Sample)")
    except Exception as e:
        st.warning(f"Could not load data quality summary: {e}")
    
    # --- 1. INITIAL SETUP & GLOBAL FILTERS ---
    
    # Fetch initial options for selectboxes
    q_options = "SELECT DISTINCT STATE, YEAR, QUARTER FROM aggregated_insurance_record;"
    try:
        df_options = pd.read_sql(q_options,connection)
    except Exception as e:
        st.error(f"Error connecting to database or querying options: {e}. Ensure 'aggregated_insurance_record' table exists.")
        return

    if df_options.empty:
        st.warning("No insurance data available to plot.")
        return

    # Setup Filter Options
    state_options = ['All'] + sorted(df_options['STATE'].unique().tolist())
    year_options = ['All'] + sorted(df_options['YEAR'].unique().tolist())
    
    col1, col2 = st.columns(2)
    with col1:
        selected_state_filter = st.selectbox("Select State (Global Filter)", state_options, key='ins_state_filter')
    with col2:
        selected_year_filter = st.selectbox("Select Year (Global Filter)", year_options, key='ins_year_filter')

    # Construct Title Suffixes
    year_suffix = selected_year_filter if selected_year_filter != 'All' else 'All Years'
    state_suffix = selected_state_filter if selected_state_filter != 'All' else 'All States'
    filter_label = f" in {state_suffix}, {year_suffix}"

    # --- 2. DYNAMIC SQL QUERY (Foundation for Plots 1, 2, 5) ---
    base_query_state_agg = """
        SELECT STATE, 
               SUM(INSURANCE_COUNT) AS total_count,
               SUM(insurance_amount) AS total_amount
        FROM aggregated_insurance_record
    """
    where_clauses = []
    parameters = []

    if selected_state_filter != 'All':
        where_clauses.append("STATE = %s")
        parameters.append(selected_state_filter)

    if selected_year_filter != 'All':
        where_clauses.append("YEAR = %s")
        parameters.append(selected_year_filter)
    
    if where_clauses:
        base_query_state_agg += " WHERE " + " AND ".join(where_clauses)
    
    base_query_state_agg += " GROUP BY STATE HAVING SUM(INSURANCE_COUNT) > 0 ORDER BY total_count DESC;"
    query_params = tuple(parameters) if parameters else None

    try:
        df_state_data = pd.read_sql(base_query_state_agg,connection, params=query_params)
    except Exception as e:
        st.error(f"Error executing state aggregation query: {e}")
        return

    if df_state_data.empty:
        st.info("No aggregated state data for the selected filters.")
        return

    # Calculate Average Policy Value
    df_state_data['Average_Policy_Value'] = df_state_data['total_amount'] / df_state_data['total_count']

    st.subheader("5a. Top States by Insurance Transaction Volume and Value")
    
    df_top_states = df_state_data.nlargest(10, 'total_count').copy()
    title_chart = f"Top 10 States by Insurance Uptake and Value{filter_label}"

    fig1 = go.Figure()

    fig1.add_trace(go.Bar(
        x=df_top_states['STATE'],
        y=df_top_states['total_count'],
        name='Transaction Volume (Count)',
        marker_color='mediumseagreen',
        hovertemplate="<b>%{x}</b><br>Volume: %{y:,.0f}<br>Value: ₹%{customdata[0]:,.2f}<extra></extra>",
        customdata=df_top_states[['total_amount']].values
    ))

    # Trace 2: Transaction Value (Line Chart, right y-axis)
    fig1.add_trace(go.Scatter(
        x=df_top_states['STATE'],
        y=df_top_states['total_amount'],
        name='Transaction Value (Premium)',
        mode='lines+markers',
        yaxis='y2',
        line=dict(color='darkblue'),
        hovertemplate="<b>%{x}</b><br>Volume: %{customdata[0]:,.0f}<br>Value: ₹%{y:,.2f}<extra></extra>",
        customdata=df_top_states[['total_count']].values
    ))
    
    # Update layout for dual Y-axis
    fig1.update_layout(
        title=title_chart,
        xaxis_title="State",
        yaxis=dict(title='Transaction Volume (Count)', title_font=dict(color='mediumseagreen')),
        yaxis2=dict(
            title='Transaction Value (INR)',
            title_font=dict(color='darkblue'),
            overlaying='y',
            side='right',
            tickformat=',.2s'
        ),
        legend=dict(x=0.01, y=0.99)
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("---")

    st.subheader("5b. State Strategy Scatter Plot (Volume vs. Average Policy Value)")
    st.info("💡 **Strategy:** Focus on **High Volume/Low Avg Value** states (bottom-right) for premium-boosting offers.")
    
    df_scatter = df_state_data[df_state_data['total_count'] > 1000].copy() 

    if not df_scatter.empty:
        fig_scatter = px.scatter(
            df_scatter,
            x='total_count',
            y='Average_Policy_Value',
            color='STATE',
            size='total_amount',
            hover_name='STATE',
            title=f"Insurance Volume vs. Average Policy Value{filter_label}",
            labels={
                'total_count': 'Transaction Volume (Uptake)', 
                'Average_Policy_Value': 'Average Policy Value (INR)'
            }
        )
        
        fig_scatter.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>Volume: %{x:,.0f}<br>Avg Value: ₹%{y:,.2f}<br>Total Value: ₹%{customdata[0]:,.2f}<extra></extra>",
            customdata=df_scatter[['total_amount']]
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Insufficient data to generate the strategy scatter plot.")
    
    st.markdown("---")

    st.subheader("5c. Quarterly Trend: Insurance Transaction Volume Growth")
    
    base_query_trend = """
        SELECT YEAR, QUARTER, SUM(INSURANCE_COUNT) AS total_count
        FROM aggregated_insurance_record
    """
    if where_clauses:
        base_query_trend += " WHERE " + " AND ".join(where_clauses)
    
    base_query_trend += " GROUP BY YEAR, QUARTER ORDER BY YEAR, QUARTER;"
    
    try:
        df_trend = pd.read_sql(base_query_trend,connection, params=query_params)
    except Exception as e:
        st.warning(f"Could not run trend query: {e}")
        df_trend = pd.DataFrame()

    if not df_trend.empty:
        df_trend['Period'] = df_trend['YEAR'].astype(str) + '-Q' + df_trend['QUARTER'].astype(str)
        
        fig_trend = px.line(
            df_trend, 
            x='Period', 
            y='total_count', 
            title=f"Insurance Transaction Volume Trend{filter_label}",
            markers=True,
            labels={'total_count': 'Total Transaction Count', 'Period': 'Time Period'}
        )
        fig_trend.update_traces(
            hovertemplate="<b>%{x}</b><br>Transactions: %{y:,.0f}<extra></extra>"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Insufficient data to generate the quarterly trend analysis.")

    st.markdown("---")
    
    st.subheader("5d. Top 10 Districts by Insurance Transaction Count")
    
    if selected_state_filter == 'All' and not df_options['STATE'].empty:
        most_active_state = df_state_data.iloc[0]['STATE'] if not df_state_data.empty else sorted(df_options['STATE'].unique().tolist())[0]
        st.info(f"Drilling down into the top district markets of: **{most_active_state}**")
        drill_state = most_active_state
    else:
        drill_state = selected_state_filter

    base_query_district = """
        SELECT ENTITY_NAME AS District, SUM(INSURANCE_COUNT) AS total_count, SUM(INSURANCE_AMOUNT) AS total_amount
        FROM top_insurance_record
        WHERE STATE = %s AND ENTITY_TYPE = 'District'
    """
    parameters_district = [drill_state]

    if selected_year_filter != 'All':
        base_query_district += " AND YEAR = %s"
        parameters_district.append(selected_year_filter)

    base_query_district += " GROUP BY ENTITY_NAME ORDER BY total_count DESC LIMIT 10;"

    try:
        df_district = pd.read_sql(base_query_district,connection, params=tuple(parameters_district))
    except Exception as e:
        st.warning(f"Could not query district data from 'top_insurance_record': {e}")
        df_district = pd.DataFrame()
        
    if not df_district.empty:
        fig_district = go.Figure()

        fig_district.add_trace(go.Bar(
            x=df_district['District'],
            y=df_district['total_count'],
            name='Transaction Volume (Count)',
            marker_color='mediumseagreen',
        ))
        fig_district.update_traces(
            hovertemplate="<b>%{x}</b><br>Count: %{y:,.0f}<extra></extra>",
            selector=dict(type='bar')
        )

        fig_district.add_trace(go.Scatter(
            x=df_district['District'],
            y=df_district['total_amount'],
            name='Transaction Value (Premium)',
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='darkblue'),
            hovertemplate="<b>%{x}</b><br>Volume: %{customdata[0]:,.0f}<br>Value: ₹%{y:,.2f}<extra></extra>",
            customdata=df_district[['total_count']].values
        ))

        fig_district.update_layout(
            title='Top 10 Districts by Insurance Volume and Value',
            xaxis_title="District Name",
            yaxis=dict(
                title='Transaction Volume (Count)',
                title_font=dict(color='mediumseagreen'),
                tickfont=dict(color='mediumseagreen')
            ),
            yaxis2=dict(
                title='Transaction Value (Premium, INR)',
                title_font=dict(color='darkblue'),
                tickfont=dict(color='darkblue'),
                overlaying='y',
                side='right',
                tickformat=',.2s'
            ),
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig_district, use_container_width=True)
    else:
        st.info(f"No district-level data available for {drill_state}.")
    
    st.markdown("---")

    st.subheader("5e. Top 10 States by Average Policy Value")
    df_avg_sort = df_state_data.sort_values('Average_Policy_Value', ascending=False).nlargest(10, 'Average_Policy_Value').copy()

    fig_fallback = px.bar(
        df_avg_sort, 
        x='STATE', 
        y='Average_Policy_Value', 
        title=f"Top 10 States by Average Policy Value{filter_label}",
        labels={'Average_Policy_Value': 'Avg Policy Value (INR)', 'STATE': 'State Name'},
        color='Average_Policy_Value',
        color_continuous_scale=px.colors.sequential.Viridis
    )
    fig_fallback.update_traces(hovertemplate="<b>%{x}</b><br>Avg Value: ₹%{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_fallback, use_container_width=True)

    st.markdown("---")

    # --- 8. PLOT 5: Policy Value Concentration (Pie Chart) ---
    st.subheader("6f. Policy Value Concentration (State Share by Amount)")
    
    total_value_global = df_state_data['total_amount'].sum()

    if total_value_global > 0:
        df_share = df_state_data.copy()
        df_share['percentage'] = (df_share['total_amount'] / total_value_global) * 100
        
        if len(df_share) > 10:
            df_top_share = df_share.nlargest(10, 'percentage').copy()
            other_percentage = df_share['percentage'].sum() - df_top_share['percentage'].sum()
            
            df_top_share = pd.concat([
                df_top_share, 
                pd.DataFrame([{'STATE': 'Other States', 'percentage': other_percentage, 'total_amount': 0}])
            ])
        else:
            df_top_share = df_share
        
        fig_share = px.pie(
            df_top_share, 
            values='percentage', 
            names='STATE', 
            title=f"Insurance Value Concentration by Top States{filter_label}",
            hole=0.4
        )
        fig_share.update_traces(
            hovertemplate="<b>%{label}</b><br>Value: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>",
            customdata=df_top_share['total_amount']
        )
        st.plotly_chart(fig_share, use_container_width=True)
    else:
        st.info("No policy value data available to calculate state concentration.")
