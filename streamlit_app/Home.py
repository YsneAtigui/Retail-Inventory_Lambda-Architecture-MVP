"""
Retail Analytics Dashboard - Home Page
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.db_connector import test_connection, execute_query, get_data_freshness
from utils.metrics import format_currency, format_number
from utils.charts import create_metric_card

# Page configuration
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
    }
    h1 {
        color: #667eea;
        font-weight: 700;
    }
    .architecture-box {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📊 Retail Analytics Dashboard")
st.markdown("### Lambda Architecture - Real-time & Batch Analytics")

# Connection status
with st.spinner("Connecting to ClickHouse..."):
    is_connected = test_connection()

if is_connected:
    st.success("✅ Connected to ClickHouse")
else:
    st.error("❌ Failed to connect to ClickHouse. Please ensure the database is running.")
    st.info(f"Connection: {config.CLICKHOUSE_HOST}:{config.CLICKHOUSE_PORT}/{config.CLICKHOUSE_DATABASE}")
    st.stop()

# Get key metrics
st.markdown("---")
st.markdown("## 📈 Key Metrics Overview")

col1, col2, col3, col4 = st.columns(4)

# Query for key metrics
metrics_query = """
SELECT
    count() as total_transactions,
    sum(quantity * unit_price) as total_revenue,
    countDistinct(product_id) as unique_products,
    countDistinct(store_id) as unique_stores
FROM retail_events_unified
WHERE transaction_type = 'SALE'
"""

df_metrics = execute_query(metrics_query)

if df_metrics is not None and not df_metrics.empty:
    total_transactions = int(df_metrics['total_transactions'].iloc[0])
    total_revenue = float(df_metrics['total_revenue'].iloc[0])
    unique_products = int(df_metrics['unique_products'].iloc[0])
    unique_stores = int(df_metrics['unique_stores'].iloc[0])
    
    with col1:
        st.metric(
            label="💰 Total Revenue",
            value=format_currency(total_revenue),
            delta=None
        )
    
    with col2:
        st.metric(
            label="🛒 Total Transactions",
            value=format_number(total_transactions),
            delta=None
        )
    
    with col3:
        st.metric(
            label="📦 Unique Products",
            value=format_number(unique_products),
            delta=None
        )
    
    with col4:
        st.metric(
            label="🏪 Active Stores",
            value=format_number(unique_stores),
            delta=None
        )

# Data freshness
st.markdown("---")
st.markdown("## 🕒 System Status")

freshness = get_data_freshness()
if freshness:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(create_metric_card(
            "Latest Event Time",
            str(freshness.get('latest_event', 'N/A'))
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card(
            "Total Records (Real-time)",
            format_number(freshness.get('total_records', 0))
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card(
            "Last Insert Time",
            str(freshness.get('latest_insert', 'N/A'))
        ), unsafe_allow_html=True)

# Architecture overview
st.markdown("---")
st.markdown("## 🏗️ Architecture Overview")

st.markdown("""
<div class="architecture-box">
<h4>Lambda Architecture Components</h4>
<ul>
    <li><strong>Speed Layer:</strong> Kafka → ClickHouse (Real-time processing)</li>
    <li><strong>Batch Layer:</strong> Spark → MinIO → ClickHouse (Historical data)</li>
    <li><strong>Serving Layer:</strong> Unified views combining real-time + batch data</li>
    <li><strong>ML Layer:</strong> Demand forecasting predictions and model metrics</li>
</ul>
</div>
""", unsafe_allow_html=True)

# Available dashboards
st.markdown("---")
st.markdown("## 📱 Available Dashboards")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📊 Real-Time Sales
    - Live sales monitoring
    - Hourly trends
    - Category breakdown
    - Top products
    - Store performance
    
    ### 🤖 ML Predictions
    - Demand forecasting
    - Model performance metrics
    - Prediction accuracy
    - Restock recommendations
    """)

with col2:
    st.markdown("""
    ### 📈 Historical Analysis
    - Daily sales trends
    - Peak hours heatmap
    - Store comparisons
    - Return rate analysis
    
    ### 🎯 Anomaly Detection
    - Sales anomaly alerts
    - Confidence bands
    - Category-wise analysis
    - Alert configuration
    """)

st.markdown("""
    ### 📦 Inventory Insights
    - Stock status overview
    - Stock movement analysis
    - High/low demand products
    - Restock priority matrix
    """)

# Quick actions
st.markdown("---")
st.markdown("## 🚀 Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("📊 View Tables", use_container_width=True):
        from utils.db_connector import get_table_list
        tables = get_table_list()
        st.write(f"Found {len(tables)} tables/views:")
        st.write(tables)

with col3:
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 20px;">
    <p>Retail Inventory Analytics Dashboard | Lambda Architecture MVP</p>
    <p>Powered by ClickHouse, Kafka, Spark, and Streamlit</p>
</div>
""", unsafe_allow_html=True)
