import pandas as pd
import numpy as np
import streamlit as st

def detect_outliers_iqr(df, column):
    """Detect outliers using IQR method"""
    if column not in df.columns or df[column].isna().all():
        return pd.DataFrame(), 0, 0, 0
    
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    return outliers, lower_bound, upper_bound, len(outliers)


def detect_outliers_zscore(df, column, threshold=3):
    """Detect extreme outliers using Z-score method"""
    if column not in df.columns or df[column].isna().all():
        return pd.DataFrame(), 0
    
    from scipy import stats
    z_scores = np.abs(stats.zscore(df[column].dropna()))
    outlier_indices = np.where(z_scores > threshold)[0]
    outliers = df.iloc[outlier_indices]
    return outliers, len(outliers)


def show_data_quality_summary(df, data_name):
    """Display data quality summary with IQR and Z-score outlier detection"""
    with st.expander(f"📊 Data Quality Summary: {data_name}", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", f"{len(df):,}")
        with col2:
            st.metric("Total Columns", len(df.columns))
        with col3:
            st.metric("Missing Values", df.isnull().sum().sum())
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            st.write("**📈 Statistical Summary (Numeric Columns):**")
            st.dataframe(df[numeric_cols].describe().style.format("{:.2f}"))
            
            st.write("**🔍 IQR Outlier Detection:**")
            outlier_summary = []
            
            for col in numeric_cols:
                if len(df[col].dropna()) > 0:
                    outliers, lower, upper, count = detect_outliers_iqr(df, col)
                    outlier_pct = (count / len(df)) * 100 if len(df) > 0 else 0
                    outlier_summary.append({
                        'Column': col,
                        'Outlier Count': count,
                        'Outlier %': f"{outlier_pct:.2f}%",
                        'Lower Bound': f"{lower:,.2f}",
                        'Upper Bound': f"{upper:,.2f}",
                        'Min': f"{df[col].min():,.2f}",
                        'Max': f"{df[col].max():,.2f}"
                    })
            
            if outlier_summary:
                st.dataframe(pd.DataFrame(outlier_summary))
            
            st.write("**⚠️ Z-Score Extreme Outliers (>3σ):**")
            extreme_outliers = []
            for col in numeric_cols:
                if len(df[col].dropna()) > 0:
                    _, zscore_count = detect_outliers_zscore(df, col, threshold=3)
                    zscore_pct = (zscore_count / len(df)) * 100 if len(df) > 0 else 0
                    if zscore_count > 0:
                        extreme_outliers.append(f"• **{col}**: {zscore_count} extreme outliers ({zscore_pct:.2f}%)")
            
            if extreme_outliers:
                for item in extreme_outliers:
                    st.markdown(item)
            else:
                st.info("✅ No extreme outliers detected (all values within 3σ)")
        
        st.markdown("---")
