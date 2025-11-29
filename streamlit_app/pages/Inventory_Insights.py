"""
Inventory Insights Dashboard
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
from utils.metrics import format_currency, format_number
from utils.charts import create_pie_chart, create_bar_chart, create_scatter_chart

# Page configuration
st.set_page_config(
    page_title="Inventory Insights | Retail Analytics",
    page_icon="📦",
    layout="wide"
)

# Title
st.title("📦 Inventory Insights Dashboard")
st.markdown("### Inventory management and stock movement analysis")

st.markdown("---")

# Stock Movement Overview
st.markdown("## 📊 Stock Movement Overview")

movement_query = """
SELECT
    transaction_type,
    count() as transaction_count,
    sum(quantity) as total_quantity,
    sum(quantity * unit_price) as total_value
FROM retail_events_unified
WHERE toDate(event_time) >= today() - INTERVAL 30 DAY
GROUP BY transaction_type
ORDER BY total_quantity DESC
"""

df_movement = execute_query(movement_query)

if df_movement is not None and not df_movement.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        fig_movement = create_pie_chart(
            df_movement,
            values='total_quantity',
            names='transaction_type',
            title='Stock Movement by Type (Last 30 Days)',
            height=400,
            hole=0.4
        )
        st.plotly_chart(fig_movement, use_container_width=True)
    
    with col2:
        st.markdown("### Movement Details")
        st.dataframe(
            df_movement.style.format({
                'transaction_count': '{:,.0f}',
                'total_quantity': '{:,.0f}',
                'total_value': lambda x: format_currency(x)
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Calculate net movement
        sales_qty = df_movement[df_movement['transaction_type'] == 'SALE']['total_quantity'].sum() if 'SALE' in df_movement['transaction_type'].values else 0
        return_qty = df_movement[df_movement['transaction_type'] == 'RETURN']['total_quantity'].sum() if 'RETURN' in df_movement['transaction_type'].values else 0
        restock_qty = df_movement[df_movement['transaction_type'] == 'RESTOCK']['total_quantity'].sum() if 'RESTOCK' in df_movement['transaction_type'].values else 0
        
        net_movement = restock_qty - sales_qty + return_qty
        
        st.metric(
            "Net Stock Movement",
            f"{int(net_movement):,} units",
            delta=f"{'Increase' if net_movement > 0 else 'Decrease'}"
        )

st.markdown("---")

# High Demand Products
st.markdown("## 🔥 High Demand Products")

high_demand_query = """
WITH sales_data AS (
    SELECT
        product_id,
        category,
        sum(quantity) as total_sold_30d,
        count() as transaction_count
    FROM retail_events_unified
    WHERE transaction_type = 'SALE'
        AND toDate(event_time) >= today() - INTERVAL 30 DAY
    GROUP BY product_id, category
),
predictions AS (
    SELECT
        product_id,
        sum(predicted_demand) as predicted_7d
    FROM demand_predictions
    WHERE forecast_date BETWEEN today() AND today() + INTERVAL 7 DAY
    GROUP BY product_id
)
SELECT
    s.product_id,
    s.category,
    s.total_sold_30d,
    coalesce(p.predicted_7d, 0) as predicted_7d,
    s.transaction_count,
    (s.total_sold_30d / 30.0) as avg_daily_sales
FROM sales_data s
LEFT JOIN predictions p ON s.product_id = p.product_id
ORDER BY s.total_sold_30d DESC
LIMIT 20
"""

df_high_demand = execute_query(high_demand_query)

if df_high_demand is not None and not df_high_demand.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_high_demand = create_bar_chart(
            df_high_demand.head(10),
            x='product_id',
            y='total_sold_30d',
            title='Top 10 Products by Sales Volume (Last 30 Days)',
            height=400
        )
        st.plotly_chart(fig_high_demand, use_container_width=True)
    
    with col2:
        st.markdown("### Product Details")
        st.dataframe(
            df_high_demand.head(10).style.format({
                'total_sold_30d': '{:,.0f}',
                'predicted_7d': '{:.0f}',
                'transaction_count': '{:,.0f}',
                'avg_daily_sales': '{:.1f}'
            }),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No high demand product data available.")

st.markdown("---")

# Slow Moving Products
st.markdown("## 🐌 Slow Moving Products")

slow_moving_query = """
WITH sales_data AS (
    SELECT
        product_id,
        category,
        sum(quantity) as total_sold_30d,
        count() as transaction_count,
        datediff('day', min(event_time), max(event_time)) as days_active
    FROM retail_events_unified
    WHERE transaction_type = 'SALE'
        AND toDate(event_time) >= today() - INTERVAL 30 DAY
    GROUP BY product_id, category
    HAVING total_sold_30d > 0
)
SELECT
    product_id,
    category,
    total_sold_30d,
    transaction_count,
    days_active,
    total_sold_30d / nullIf(days_active, 0) as avg_daily_sales
FROM sales_data
WHERE days_active > 5
ORDER BY avg_daily_sales ASC
LIMIT 20
"""

df_slow = execute_query(slow_moving_query)

if df_slow is not None and not df_slow.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_slow = create_bar_chart(
            df_slow.head(10),
            x='product_id',
            y='avg_daily_sales',
            title='Bottom 10 Products by Daily Sales Rate',
            height=400
        )
        st.plotly_chart(fig_slow, use_container_width=True)
    
    with col2:
        st.markdown("### Slow Movers")
        st.dataframe(
            df_slow.head(10).style.format({
                'total_sold_30d': '{:,.0f}',
                'transaction_count': '{:,.0f}',
                'days_active': '{:.0f}',
                'avg_daily_sales': '{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.warning(f"⚠️ {len(df_slow)} products with low turnover detected")
else:
    st.info("No slow moving product data available.")

st.markdown("---")

# Restock Priority Matrix
st.markdown("## 🎯 Restock Priority Matrix")
st.markdown("Products plotted by sales volume vs predicted demand")

priority_query = """
WITH sales_data AS (
    SELECT
        product_id,
        sum(quantity) as total_sold_30d
    FROM retail_events_unified
    WHERE transaction_type = 'SALE'
        AND toDate(event_time) >= today() - INTERVAL 30 DAY
    GROUP BY product_id
),
predictions AS (
    SELECT
        product_id,
        sum(predicted_demand) as predicted_7d
    FROM demand_predictions
    WHERE forecast_date BETWEEN today() AND today() + INTERVAL 7 DAY
    GROUP BY product_id
)
SELECT
    s.product_id,
    s.total_sold_30d,
    coalesce(p.predicted_7d, 0) as predicted_7d,
    CASE
        WHEN p.predicted_7d > s.total_sold_30d / 30 * 7 * 1.2 THEN 'High Priority'
        WHEN p.predicted_7d > s.total_sold_30d / 30 * 7 * 0.8 THEN 'Normal'
        ELSE 'Low Priority'
    END as priority
FROM sales_data s
LEFT JOIN predictions p ON s.product_id = p.product_id
WHERE s.total_sold_30d > 0
ORDER BY predicted_7d DESC
LIMIT 50
"""

df_priority = execute_query(priority_query)

if df_priority is not None and not df_priority.empty:
    fig_priority = create_scatter_chart(
        df_priority,
        x='total_sold_30d',
        y='predicted_7d',
        title='Restock Priority Matrix: Historical Sales vs Predicted Demand',
        color='priority',
        size='predicted_7d',
        height=500
    )
    st.plotly_chart(fig_priority, use_container_width=True)
    
    # Priority breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        high_priority = len(df_priority[df_priority['priority'] == 'High Priority'])
        st.metric("🔴 High Priority", high_priority)
    
    with col2:
        normal_priority = len(df_priority[df_priority['priority'] == 'Normal'])
        st.metric("🟡 Normal Priority", normal_priority)
    
    with col3:
        low_priority = len(df_priority[df_priority['priority'] == 'Low Priority'])
        st.metric("🟢 Low Priority", low_priority)
else:
    st.info("No restock priority data available. Ensure ML predictions are present.")

st.markdown("---")

# Category Stock Status
st.markdown("## 📋 Category Stock Status")

category_query = """
SELECT
    category,
    countIf(transaction_type = 'SALE') as sales_count,
    countIf(transaction_type = 'RETURN') as return_count,
    countIf(transaction_type = 'RESTOCK') as restock_count,
    sumIf(quantity, transaction_type = 'SALE') as total_sold,
    sumIf(quantity, transaction_type = 'RETURN') as total_returned,
    sumIf(quantity, transaction_type = 'RESTOCK') as total_restocked
FROM retail_events_unified
WHERE toDate(event_time) >= today() - INTERVAL 30 DAY
GROUP BY category
ORDER BY total_sold DESC
"""

df_category_stock = execute_query(category_query)

if df_category_stock is not None and not df_category_stock.empty:
    # Calculate net stock
    df_category_stock['net_stock_change'] = (
        df_category_stock['total_restocked'] - 
        df_category_stock['total_sold'] + 
        df_category_stock['total_returned']
    )
    
    st.dataframe(
        df_category_stock.style.format({
            'sales_count': '{:,.0f}',
            'return_count': '{:,.0f}',
            'restock_count': '{:,.0f}',
            'total_sold': '{:,.0f}',
            'total_returned': '{:,.0f}',
            'total_restocked': '{:,.0f}',
            'net_stock_change': '{:,.0f}'
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No category stock data available.")

# Footer
st.markdown("---")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("*Inventory insights based on last 30 days of transaction data*")
