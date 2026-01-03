import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
from outliers_detection import show_data_quality_summary
import plotly.graph_objects as go


def plot_device_dominance(connection):
    """
    Performs a comprehensive EDA on device dominance and user engagement (AOPD),
    combining filter setup, dynamic SQL querying, and five distinct Plotly visualizations 
    to address the business scenario.
    Enhanced with IQR and Z-score outlier detection.
    """
    st.header("2. Device Dominance and User Engagement Analysis")
    st.write("**Scenario Goal:** Understand device preferences and identify underutilized/highly engaged brands to enhance app performance and engagement.")
    
    # --- DATA QUALITY SUMMARY (NEW - Outlier Detection) ---
    try:
        base_query_sample = "SELECT * FROM aggregated_user_record;"
        df_sample = pd.read_sql(base_query_sample,connection)
        show_data_quality_summary(df_sample, "User Device Data (Sample)")
    except Exception as e:
        st.warning(f"Could not load data quality summary: {e}")
    
    
    # Fetch initial options for selectboxes
    q_options = "SELECT DISTINCT STATE, YEAR FROM aggregated_user_record;"
    try:
        df_options = pd.read_sql(q_options,connection)
    except Exception as e:
        st.error(f"Error connecting to database or querying options: {e}")
        return

    # Setup Filter Options
    state_options = ['All'] + sorted(df_options['STATE'].unique().tolist())
    year_options = ['All'] + sorted(df_options['YEAR'].unique().tolist())
    
    col1, col2 = st.columns(2)
    with col1:
        selected_state = st.selectbox("Filter by State", state_options, key='device_state_filter_sql')
    with col2:
        selected_year = st.selectbox("Filter by Year", year_options, key='device_year_filter_sql')

    
    base_query = """
        SELECT DEVICE_BRAND, 
               SUM(DEVICE_COUNT) AS total_device_count,
               SUM(APPS_OPEN) AS total_app_opens
        FROM aggregated_user_record
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
    
    base_query += " GROUP BY DEVICE_BRAND ORDER BY total_device_count DESC;"
    query_params = tuple(parameters) if parameters else None

    try:
        df_device_data = pd.read_sql(base_query,connection, params=query_params)
    except Exception as e:
        st.error(f"Error executing device dominance query: {e}")
        return

    if df_device_data.empty:
        st.info("No device data for the selected filters.")
        return

    # Calculate Engagement Ratio (App Opens Per Device - AOPD)
    # Calculate Engagement Ratio (App Opens Per Device - AOPD)
    # Ensure columns are numeric to avoid TypeErrors
    df_device_data['total_device_count'] = pd.to_numeric(df_device_data['total_device_count'], errors='coerce').fillna(0)
    df_device_data['total_app_opens'] = pd.to_numeric(df_device_data['total_app_opens'], errors='coerce').fillna(0)

    # Use vectorized calculation for better performance and safety
    df_device_data['Engagement_Ratio'] = 0.0
    valid_mask = df_device_data['total_device_count'] > 0
    df_device_data.loc[valid_mask, 'Engagement_Ratio'] = (
        df_device_data.loc[valid_mask, 'total_app_opens'] / 
        df_device_data.loc[valid_mask, 'total_device_count']
    )
    
    # Construct Title Suffixes
    year_suffix = selected_year if selected_year != 'All' else 'All Years'
    state_suffix = selected_state if selected_state != 'All' else 'All States'
    filter_label = f" in {state_suffix}, {year_suffix}"

    st.subheader("2a. Top 10 Device Brands by Total Device Count (Volume)")
    
    df_brand_count = df_device_data.nlargest(10, 'total_device_count').copy()
    title_bar = f"Top 10 Brands by Device Count{filter_label}"

    fig_brand = px.bar(
        df_brand_count, 
        x='DEVICE_BRAND', 
        y='total_device_count', 
        title=title_bar,
        labels={'total_device_count': 'Total Device Count', 'DEVICE_BRAND': 'Device Brand'},
        color='DEVICE_BRAND'
    )
    fig_brand.update_traces(
        hovertemplate="<b>%{x}</b><br>Total Devices: %{y:,.0f}<extra></extra>"
    )
    st.plotly_chart(fig_brand, use_container_width=True)
    st.markdown("---")

    st.subheader("2b. Device Brand Share Distribution (Percentage Share)")
    
    total_devices = df_device_data['total_device_count'].sum()
    
    if total_devices > 0:
        df_device_data['percentage'] = (df_device_data['total_device_count'] / total_devices) * 100
        
        # Calculate 'Other' category for top 10 for cleaner visualization
        df_top_brands_pie = df_device_data.nlargest(10, 'percentage').copy()
        other_percentage = df_device_data['percentage'].sum() - df_top_brands_pie['percentage'].sum()
        
        if other_percentage > 0:
            df_top_brands_pie = pd.concat([
                df_top_brands_pie, 
                pd.DataFrame([{'DEVICE_BRAND': 'Other', 'percentage': other_percentage, 'total_device_count': 0}])
            ])
        
        fig_pie = px.pie(
            df_top_brands_pie, 
            values='percentage', 
            names='DEVICE_BRAND', 
            title=f"Device Share Distribution{filter_label}",
            hole=0.3
        )
        fig_pie.update_traces(
            hovertemplate="<b>%{label}</b><br>Share: %{percent}<br>Percentage: %{value:.2f}%<extra></extra>"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    st.markdown("---")
    
    
    st.subheader("2c. Device Brand Growth Trend Over Time")
    st.info("💡 **Insight:** Track how device market share evolves quarter-over-quarter")

    # Fetch time-series data for top brands
    if selected_state != 'All':
        trend_query = f"""
            SELECT 
                DEVICE_BRAND,
                YEAR,
                QUARTER,
                CONCAT(YEAR, '-Q', QUARTER) AS period,
                SUM(DEVICE_COUNT) AS device_count
            FROM aggregated_user_record
            WHERE STATE = %s
            GROUP BY DEVICE_BRAND, YEAR, QUARTER
            ORDER BY YEAR, QUARTER
        """
        query_params_trend = (selected_state,)
    else:
        trend_query = """
            SELECT 
                DEVICE_BRAND,
                YEAR,
                QUARTER,
                CONCAT(YEAR, '-Q', QUARTER) AS period,
                SUM(DEVICE_COUNT) AS device_count
            FROM aggregated_user_record
            GROUP BY DEVICE_BRAND, YEAR, QUARTER
            ORDER BY YEAR, QUARTER
        """
        query_params_trend = None

        df_trend = pd.read_sql(trend_query, connection, params=query_params_trend)
        
        if not df_trend.empty:
            # Get top 7 brands overall
            top_brands_overall = df_trend.groupby('DEVICE_BRAND')['device_count'].sum().nlargest(7).index.tolist()
            df_trend_filtered = df_trend[df_trend['DEVICE_BRAND'].isin(top_brands_overall)]
            
            # Create line chart
            fig_trend = px.line(
                df_trend_filtered,
                x='period',
                y='device_count',
                color='DEVICE_BRAND',
                title=f"Device Brand Growth Trend{filter_label}",
                labels={
                    'device_count': 'Device Count',
                    'period': 'Time Period',
                    'DEVICE_BRAND': 'Brand'
                },
                markers=True
            )
            
            fig_trend.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>" +
                            "Period: %{x}<br>" +
                            "Devices: %{y:,.0f}<extra></extra>"
            )
            
            fig_trend.update_layout(
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
    
    st.subheader("2d. Market Concentration Analysis")
    st.info("💡 **Business Value:** Understand market competition - Low HHI = Healthy competition, High HHI = Market dominated by few brands")

    # Calculate market share and concentration metrics
    df_concentration = df_device_data.copy()
    total_devices = df_concentration['total_device_count'].sum()

    if total_devices > 0:
        df_concentration['market_share_pct'] = (df_concentration['total_device_count'] / total_devices * 100)
        df_concentration['market_share_squared'] = df_concentration['market_share_pct'] ** 2
        
        # Herfindahl-Hirschman Index (HHI)
        hhi = df_concentration['market_share_squared'].sum()
        
        # Top 3 market share (CR3)
        cr3 = df_concentration.nlargest(3, 'market_share_pct')['market_share_pct'].sum()
        
        # Interpretation
        if hhi < 1500:
            market_status = "🟢 Competitive Market"
            market_desc = "Healthy competition with no dominant players"
        elif hhi < 2500:
            market_status = "🟡 Moderate Concentration"
            market_desc = "Some brands have significant market power"
        else:
            market_status = "🔴 High Concentration"
            market_desc = "Market dominated by few brands"
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "HHI Score",
                f"{hhi:,.0f}",
                help="Herfindahl-Hirschman Index (0-10,000). Lower = more competitive"
            )
        
        with col2:
            st.metric(
                "Top 3 Share (CR3)",
                f"{cr3:.1f}%",
                help="Combined market share of top 3 brands"
            )
        
        with col3:
            st.metric(
                "Market Status",
                market_status.split()[1],
                help=market_desc
            )
        
        # Waterfall chart showing cumulative market share
        df_waterfall = df_concentration.nlargest(10, 'market_share_pct').copy()
        df_waterfall['cumulative_share'] = df_waterfall['market_share_pct'].cumsum()
        
        fig_concentration = go.Figure()
        
        # Bars for each brand
        fig_concentration.add_trace(go.Bar(
            x=df_waterfall['DEVICE_BRAND'],
            y=df_waterfall['market_share_pct'],
            name='Market Share',
            marker_color='lightblue',
            text=df_waterfall['market_share_pct'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside',
            hovertemplate="<b>%{x}</b><br>" +
                        "Market Share: %{y:.2f}%<extra></extra>"
        ))
        
        # Line for cumulative share
        fig_concentration.add_trace(go.Scatter(
            x=df_waterfall['DEVICE_BRAND'],
            y=df_waterfall['cumulative_share'],
            name='Cumulative Share',
            mode='lines+markers',
            marker=dict(size=8, color='orange'),
            line=dict(width=3, color='orange'),
            yaxis='y2',
            hovertemplate="<b>%{x}</b><br>" +
                        "Cumulative: %{y:.2f}%<extra></extra>"
        ))
        
        fig_concentration.update_layout(
            title=f"Market Concentration Analysis{filter_label}",
            xaxis=dict(title='Device Brand', tickangle=-45),
            yaxis=dict(
                title='Market Share (%)',
                side='left',
                range=[0, max(df_waterfall['market_share_pct']) * 1.2]
            ),
            yaxis2=dict(
                title='Cumulative Share (%)',
                side='right',
                overlaying='y',
                range=[0, 100]
            ),
            legend=dict(x=0.01, y=0.99),
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig_concentration, use_container_width=True)

    st.subheader("2e. Quarterly App Open Trend for Top Brands")
    st.write("Tracks engagement changes over time for the top 5 most used brands.")

    # SQL to get quarterly trend for the top 5 brands (must query all years/quarters)
    top_5_brands = df_device_data.nlargest(5, 'total_device_count')['DEVICE_BRAND'].tolist()
    top_5_brands_tuple = tuple(top_5_brands) 

    base_query_trend = f"""
        SELECT YEAR, QUARTER, SUM(APPS_OPEN) AS total_app_opens
        FROM aggregated_user_record    """
    where_clauses_trend = []
    parameters_trend = []
    
    if selected_state != 'All':
        where_clauses_trend.append("STATE = %s")
        parameters_trend.append(selected_state)

    if where_clauses_trend:
        base_query_trend += " AND " + " AND ".join(where_clauses_trend)
    
    base_query_trend += " GROUP BY YEAR, QUARTER ORDER BY YEAR, QUARTER;"

    try:
        df_trend = pd.read_sql(base_query_trend,connection, params=tuple(parameters_trend))
    except Exception as e:
        st.warning(f"Could not run trend query: {e}")
        df_trend = pd.DataFrame()

    if not df_trend.empty:
        df_trend['Period'] = df_trend['YEAR'].astype(str) + '-Q' + df_trend['QUARTER'].astype(str)

        fig_trend = px.line(
            df_trend, 
            x='Period', 
            y='total_app_opens', 
            title=f"App Open Trend for Top 5 Brands in {state_suffix}",
            markers=True,
            labels={'total_app_opens': 'Total App Opens (Count)', 'Period': 'Time Period'}
        )
        
        fig_trend.update_traces(
            hovertemplate="<b>%{x}</b><br>App Opens: %{y:,.0f}<extra></extra>"
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Insufficient data to generate the quarterly app open trend.")
