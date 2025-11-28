"""
Anomaly Detection Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_connector import execute_query
from utils.metrics import format_currency
from utils.charts import create_line_chart

# Page configuration
st.set_page_config(
    page_title="Anomaly Detection | Retail Analytics",
    page_icon="🎯",
    layout="wide"
)

# Title
st.title("🎯 Sales Anomaly Detection Dashboard")
st.markdown("### Identify unusual sales patterns and anomalies")

# Sidebar filters
st.sidebar.markdown("### Filters")
days_back = st.sidebar.slider("Days to Analyze", 1, 30, 7)
sensitivity = st.sidebar.slider("Sensitivity (Std Dev)", 1.0, 3.0, 2.0, 0.5)

st.info(f"📅 Analyzing data from the last **{days_back} days** | Sensitivity: ±**{sensitivity}σ**")

st.markdown("---")

# Anomaly Detection Query
st.markdown("## 🔍 Detected Anomalies")

anomaly_query = f"""
WITH hourly_stats AS (
    SELECT 
        category,
        toStartOfHour(event_time) as hour,
        sum(quantity * unit_price) as hourly_revenue
    FROM retail_events_realtime
    WHERE transaction_type = 'SALE'
      AND event_time >= now() - INTERVAL {days_back} DAY
    GROUP BY category, hour
),
moving_stats AS (
    SELECT
        category,
        hour,
        hourly_revenue,
        avg(hourly_revenue) OVER (
            PARTITION BY category 
            ORDER BY hour 
            ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
        ) as moving_avg_24h,
        stddevPop(hourly_revenue) OVER (
            PARTITION BY category 
            ORDER BY hour 
            ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
        ) as std_dev_24h
    FROM hourly_stats
)
SELECT
    category,
    hour,
    hourly_revenue,
    moving_avg_24h,
    std_dev_24h,
    (hourly_revenue - moving_avg_24h) / nullIf(std_dev_24h, 0) as z_score
FROM moving_stats
WHERE abs(z_score) > {sensitivity}
    AND std_dev_24h > 0
ORDER BY hour DESC, abs(z_score) DESC
LIMIT 50
"""

df_anomalies = execute_query(anomaly_query)

if df_anomalies is not None and not df_anomalies.empty:
    # Show count of anomalies
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🚨 Total Anomalies Detected", len(df_anomalies))
    
    with col2:
        high_anomalies = len(df_anomalies[df_anomalies['z_score'] > sensitivity])
        st.metric("📈 High Revenue Anomalies", high_anomalies)
    
    with col3:
        low_anomalies = len(df_anomalies[df_anomalies['z_score'] < -sensitivity])
        st.metric("📉 Low Revenue Anomalies", low_anomalies)
    
    # Classification
    df_anomalies['anomaly_type'] = df_anomalies['z_score'].apply(
        lambda x: 'High' if x > 0 else 'Low'
    )
    
    # Display anomalies table
    st.markdown("### Recent Anomalies")
    
    def color_anomaly(row):
        if row['anomaly_type'] == 'High':
            return ['background-color: #2ecc71'] * len(row)
        else:
            return ['background-color: #e74c3c'] * len(row)
    
    st.dataframe(
        df_anomalies.head(20).style.format({
            'hourly_revenue': lambda x: format_currency(x),
            'moving_avg_24h': lambda x: format_currency(x),
            'std_dev_24h': lambda x: format_currency(x),
            'z_score': '{:.2f}'
        }).apply(color_anomaly, axis=1),
        use_container_width=True,
        hide_index=True,
        height=400
    )
else:
    st.success("✅ No significant anomalies detected in the selected time period!")

st.markdown("---")

# Category-wise Anomaly Analysis
st.markdown("## 📊 Category-wise Sales with Confidence Bands")

category_filter = st.multiselect(
    "Select Categories to Analyze",
    options=['All'] + list(df_anomalies['category'].unique()) if df_anomalies is not None and not df_anomalies.empty else ['All'],
    default=['All']
)

if 'All' in category_filter or not category_filter:
    category_filter = None

# Build time series query
timeseries_query = f"""
WITH hourly_data AS (
    SELECT 
        category,
        toStartOfHour(event_time) as hour,
        sum(quantity * unit_price) as revenue
    FROM retail_events_realtime
    WHERE transaction_type = 'SALE'
      AND event_time >= now() - INTERVAL {days_back} DAY
    {'AND category IN (' + ','.join([f"'{c}'" for c in category_filter]) + ')' if category_filter else ''}
    GROUP BY category, hour
)
SELECT
    category,
    hour,
    revenue,
    avg(revenue) OVER (
        PARTITION BY category 
        ORDER BY hour 
        ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
    ) as moving_avg,
    stddevPop(revenue) OVER (
        PARTITION BY category 
        ORDER BY hour 
        ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
    ) as std_dev
FROM hourly_data
ORDER BY hour ASC
"""

df_timeseries = execute_query(timeseries_query)

if df_timeseries is not None and not df_timeseries.empty:
    # Calculate confidence bands
    df_timeseries['upper_band'] = df_timeseries['moving_avg'] + (sensitivity * df_timeseries['std_dev'])
    df_timeseries['lower_band'] = df_timeseries['moving_avg'] - (sensitivity * df_timeseries['std_dev'])
    
    # For each category, create a chart
    categories = df_timeseries['category'].unique()
    
    for category in categories[:5]:  # Limit to 5 categories to avoid overwhelming
        df_cat = df_timeseries[df_timeseries['category'] == category]
        
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Add actual revenue
        fig.add_trace(go.Scatter(
            x=df_cat['hour'],
            y=df_cat['revenue'],
            mode='lines',
            name='Actual Revenue',
            line=dict(color='#667eea', width=2)
        ))
        
        # Add moving average
        fig.add_trace(go.Scatter(
            x=df_cat['hour'],
            y=df_cat['moving_avg'],
            mode='lines',
            name='24h Moving Avg',
            line=dict(color='#43e97b', width=2, dash='dash')
        ))
        
        # Add confidence band
        fig.add_trace(go.Scatter(
            x=df_cat['hour'].tolist() + df_cat['hour'].tolist()[::-1],
            y=df_cat['upper_band'].tolist() + df_cat['lower_band'].tolist()[::-1],
            fill='toself',
            fillcolor='rgba(102, 126, 234, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            name=f'Confidence Band (±{sensitivity}σ)',
            hoverinfo='skip'
        ))
        
        fig.update_layout(
            title=f'Sales Anomaly Detection - {category}',
            xaxis_title='Time',
            yaxis_title='Revenue ($)',
            template=config.PLOTLY_TEMPLATE,
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No time series data available for the selected filters.")

st.markdown("---")

# Anomaly Summary by Category
st.markdown("## 📋 Anomaly Summary by Category")

if df_anomalies is not None and not df_anomalies.empty:
    summary_by_category = df_anomalies.groupby('category').agg({
        'z_score': ['count', 'mean', 'max', 'min']
    }).reset_index()
    
    summary_by_category.columns = ['category', 'anomaly_count', 'avg_z_score', 'max_z_score', 'min_z_score']
    summary_by_category = summary_by_category.sort_values('anomaly_count', ascending=False)
    
    st.dataframe(
        summary_by_category.style.format({
            'anomaly_count': '{:.0f}',
            'avg_z_score': '{:.2f}',
            'max_z_score': '{:.2f}',
            'min_z_score': '{:.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

# Alert Configuration
st.markdown("---")
st.markdown("## ⚙️ Alert Configuration")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Current Settings:**
    - Sensitivity: ±{} standard deviations
    - Analysis Window: {} days
    - Moving Average: 24 hours
    """.format(sensitivity, days_back))

with col2:
    st.markdown("""
    **Interpretation:**
    - Z-Score > {} = High revenue anomaly
    - Z-Score < -{} = Low revenue anomaly
    - Adjust sensitivity to tune detection
    """.format(sensitivity, sensitivity))

# Footer
st.markdown("---")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("*Anomalies are detected using moving average and standard deviation with configurable sensitivity*")
