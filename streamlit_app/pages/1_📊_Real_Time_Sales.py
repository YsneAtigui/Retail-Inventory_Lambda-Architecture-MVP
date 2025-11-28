"""
Real-Time Sales Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_connector import execute_query
from utils.metrics import format_currency, format_number
from utils.charts import create_line_chart, create_pie_chart, create_bar_chart

# Page configuration
st.set_page_config(
    page_title="Real-Time Sales | Retail Analytics",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📊 Real-Time Sales Dashboard")
st.markdown("### Live sales monitoring and analytics")

# Common Operations Section
with st.expander("🛠️ Common Operations", expanded=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🌐 Web Interfaces")
        st.markdown("- [Airflow UI](http://localhost:8081) - admin/admin")
        st.markdown("- [MinIO Console](http://localhost:9001) - minioadmin/minioadmin")
        st.markdown("- [ClickHouse HTTP](http://localhost:8123)")
    
    with col2:
        st.markdown("#### 📊 Quick Queries")
        st.code("""# View total events
docker exec clickhouse clickhouse-client \\
  --user=default --password=password123 \\
  --query="SELECT count() FROM retail.retail_events_realtime"
""", language="bash")
    
    with col3:
        st.markdown("#### 🔄 System Commands")
        st.code("""# View producer logs
docker logs -f inventory-producer

# Trigger batch processing
docker exec airflow-webserver \\
  airflow dags trigger retail_batch_processing
""", language="bash")

st.markdown("---")

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
if auto_refresh:
    time.sleep(0.1)  # Small delay
    st.rerun()
    
# Time filter
st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
time_range = st.sidebar.selectbox(
    "Time Range",
    ["Last 1 Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
    index=2
)

# Map time range to hours
time_map = {
    "Last 1 Hour": 1,
    "Last 6 Hours": 6,
    "Last 24 Hours": 24,
    "Last 7 Days": 168
}
hours = time_map[time_range]

# Latest Events Section
st.markdown("## 🔴 Latest 5 Events")

latest_events_query = """
SELECT 
    event_time,
    store_id,
    product_id,
    category,
    transaction_type,
    quantity,
    unit_price,
    quantity * unit_price as total_value,
    inserted_at
FROM retail_events_realtime
ORDER BY inserted_at DESC
LIMIT 5
"""

df_latest = execute_query(latest_events_query, use_cache=False)

if df_latest is not None and not df_latest.empty:
    # Add emoji column based on transaction type
    df_latest['Type'] = df_latest['transaction_type'].apply(
        lambda x: f"🛒 {x}" if x == 'SALE' else f"↩️ {x}"
    )
    
    # Format the display
    display_df = df_latest[[
        'event_time', 'Type', 'store_id', 'product_id', 
        'category', 'quantity', 'unit_price', 'total_value'
    ]].copy()
    
    display_df.columns = [
        '📅 Event Time', '🔄 Type', '🏪 Store', '📦 Product',
        '🏷️ Category', '📊 Qty', '💵 Unit Price', '💰 Total'
    ]
    
    # Display as a formatted table
    st.dataframe(
        display_df.style.format({
            '💵 Unit Price': lambda x: format_currency(x),
            '💰 Total': lambda x: format_currency(x),
            '📊 Qty': '{:,.0f}',
            '🏪 Store': lambda x: f'Store {x}'
        }),
        use_container_width=True,
        hide_index=True,
        height=250
    )
else:
    st.warning("No events found in the database.")

st.markdown("---")

# KPI Metrics
st.markdown("## 📈 Key Performance Indicators")

kpi_query = f"""
SELECT
    count() as total_transactions,
    sum(quantity * unit_price) as total_revenue,
    avg(quantity * unit_price) as avg_basket_value,
    sum(quantity) as total_quantity
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
    AND event_time >= now() - INTERVAL {hours} HOUR
"""

df_kpi = execute_query(kpi_query, use_cache=not auto_refresh)

if df_kpi is not None and not df_kpi.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    total_revenue = float(df_kpi['total_revenue'].iloc[0])
    total_transactions = int(df_kpi['total_transactions'].iloc[0])
    avg_basket = float(df_kpi['avg_basket_value'].iloc[0])
    total_qty = int(df_kpi['total_quantity'].iloc[0])
    
    with col1:
        st.metric(
            label="💰 Total Revenue",
            value=format_currency(total_revenue),
            delta=None
        )
    
    with col2:
        st.metric(
            label="🛒 Transactions",
            value=format_number(total_transactions),
            delta=None
        )
    
    with col3:
        st.metric(
            label="💳 Avg Basket Value",
            value=format_currency(avg_basket),
            delta=None
        )
    
    with col4:
        st.metric(
            label="📦 Items Sold",
            value=format_number(total_qty),
            delta=None
        )

st.markdown("---")

# Hourly Sales Trend
st.markdown("## 📉 Hourly Sales Trend")

hourly_query = f"""
SELECT
    toStartOfHour(event_time) as hour,
    sum(quantity * unit_price) as revenue,
    count() as transactions
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
    AND event_time >= now() - INTERVAL {hours} HOUR
GROUP BY hour
ORDER BY hour ASC
"""

df_hourly = execute_query(hourly_query, use_cache=not auto_refresh)

if df_hourly is not None and not df_hourly.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        fig_revenue = create_line_chart(
            df_hourly,
            x='hour',
            y='revenue',
            title='Hourly Revenue Trend',
            height=350
        )
        st.plotly_chart(fig_revenue, use_container_width=True)
    
    with col2:
        fig_transactions = create_line_chart(
            df_hourly,
            x='hour',
            y='transactions',
            title='Hourly Transaction Count',
            height=350
        )
        st.plotly_chart(fig_transactions, use_container_width=True)
else:
    st.info("No hourly data available for the selected time range.")

st.markdown("---")

# Sales by Category and Store
col1, col2 = st.columns(2)

with col1:
    st.markdown("## 🏷️ Sales by Category")
    
    category_query = f"""
    SELECT
        category,
        sum(quantity * unit_price) as revenue,
        count() as transactions
    FROM retail_events_realtime
    WHERE transaction_type = 'SALE'
        AND event_time >= now() - INTERVAL {hours} HOUR
    GROUP BY category
    ORDER BY revenue DESC
    """
    
    df_category = execute_query(category_query, use_cache=not auto_refresh)
    
    if df_category is not None and not df_category.empty:
        fig_category = create_pie_chart(
            df_category,
            values='revenue',
            names='category',
            title='Revenue by Category',
            height=400,
            hole=0.4
        )
        st.plotly_chart(fig_category, use_container_width=True)
        
        # Show table
        st.dataframe(
            df_category.style.format({
                'revenue': lambda x: format_currency(x),
                'transactions': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No category data available.")

with col2:
    st.markdown("## 🏪 Sales by Store")
    
    store_query = f"""
    SELECT
        store_id,
        sum(quantity * unit_price) as revenue,
        count() as transactions
    FROM retail_events_realtime
    WHERE transaction_type = 'SALE'
        AND event_time >= now() - INTERVAL {hours} HOUR
    GROUP BY store_id
    ORDER BY revenue DESC
    LIMIT 10
    """
    
    df_store = execute_query(store_query, use_cache=not auto_refresh)
    
    if df_store is not None and not df_store.empty:
        fig_store = create_bar_chart(
            df_store,
            x='store_id',
            y='revenue',
            title='Top 10 Stores by Revenue',
            height=400
        )
        st.plotly_chart(fig_store, use_container_width=True)
        
        # Show table
        st.dataframe(
            df_store.style.format({
                'revenue': lambda x: format_currency(x),
                'transactions': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No store data available.")

st.markdown("---")

# Top Products
st.markdown("## 🌟 Top Performing Products")

products_query = f"""
SELECT
    product_id,
    category,
    sum(quantity * unit_price) as revenue,
    sum(quantity) as quantity_sold,
    count() as transactions
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
    AND event_time >= now() - INTERVAL {hours} HOUR
GROUP BY product_id, category
ORDER BY revenue DESC
LIMIT 15
"""

df_products = execute_query(products_query, use_cache=not auto_refresh)

if df_products is not None and not df_products.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_products = create_bar_chart(
            df_products.head(10),
            x='product_id',
            y='revenue',
            title='Top 10 Products by Revenue',
            height=400
        )
        st.plotly_chart(fig_products, use_container_width=True)
    
    with col2:
        st.markdown("### Product Details")
        st.dataframe(
            df_products.head(10).style.format({
                'revenue': lambda x: format_currency(x),
                'quantity_sold': '{:,.0f}',
                'transactions': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No product data available.")

# Footer with last update time
st.markdown("---")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if auto_refresh:
    st.markdown("🔄 *Auto-refresh enabled - dashboard updates every 30 seconds*")
