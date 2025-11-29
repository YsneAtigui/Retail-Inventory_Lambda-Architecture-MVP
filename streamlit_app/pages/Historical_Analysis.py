"""
Historical Analysis Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.db_connector import execute_query
from utils.metrics import format_currency, format_number, format_percentage
from utils.charts import create_line_chart, create_bar_chart, create_heatmap

# Page configuration
st.set_page_config(
    page_title="Historical Analysis | Retail Analytics",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("📈 Historical Analysis Dashboard")
st.markdown("### Deep dive into historical sales data and trends")

# Filters
st.sidebar.markdown("### Filters")
days_back = st.sidebar.slider("Days to Analyze", 7, 90, 30)

# Date range display
st.info(f"📅 Analyzing data from the last **{days_back} days**")

st.markdown("---")

# Daily Sales Trend
st.markdown("## 📊 Daily Sales Trend")

daily_query = f"""
SELECT
    toDate(event_time) as date,
    sum(quantity * unit_price) as revenue,
    count() as transactions,
    sum(quantity) as items_sold
FROM retail_events_unified
WHERE transaction_type = 'SALE'
    AND toDate(event_time) >= today() - INTERVAL {days_back} DAY
GROUP BY date
ORDER BY date ASC
"""

df_daily = execute_query(daily_query)

if df_daily is not None and not df_daily.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        fig_revenue = create_line_chart(
            df_daily,
            x='date',
            y='revenue',
            title='Daily Revenue Trend',
            height=350
        )
        st.plotly_chart(fig_revenue, use_container_width=True)
    
    with col2:
        fig_transactions = create_line_chart(
            df_daily,
            x='date',
            y='transactions',
            title='Daily Transaction Count',
            height=350
        )
        st.plotly_chart(fig_transactions, use_container_width=True)
    
    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_revenue = df_daily['revenue'].sum()
        st.metric("Total Revenue", format_currency(total_revenue))
    
    with col2:
        avg_daily_revenue = df_daily['revenue'].mean()
        st.metric("Avg Daily Revenue", format_currency(avg_daily_revenue))
    
    with col3:
        total_transactions = df_daily['transactions'].sum()
        st.metric("Total Transactions", format_number(total_transactions))
    
    with col4:
        total_items = df_daily['items_sold'].sum()
        st.metric("Total Items Sold", format_number(total_items))

else:
    st.info("No daily trend data available.")

st.markdown("---")

# Peak Hours Analysis
st.markdown("## 🔥 Peak Hours Heatmap")
st.markdown("Transaction density by day of week and hour")

peak_hours_query = f"""
SELECT
    toDayOfWeek(event_time) as day_of_week,
    toHour(event_time) as hour,
    count() as transaction_count
FROM retail_events_unified
WHERE transaction_type = 'SALE'
    AND toDate(event_time) >= today() - INTERVAL {days_back} DAY
GROUP BY day_of_week, hour
ORDER BY day_of_week, hour
"""

df_peak = execute_query(peak_hours_query)

if df_peak is not None and not df_peak.empty:
    # Map day numbers to names
    day_names = {
        1: 'Monday',
        2: 'Tuesday',
        3: 'Wednesday',
        4: 'Thursday',
        5: 'Friday',
        6: 'Saturday',
        7: 'Sunday'
    }
    df_peak['day_name'] = df_peak['day_of_week'].map(day_names)
    
    fig_heatmap = create_heatmap(
        df_peak,
        x='hour',
        y='day_name',
        z='transaction_count',
        title='Transaction Heatmap (Day vs Hour)',
        height=400,
        colorscale='YlOrRd'
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Find peak hour
    peak_row = df_peak.loc[df_peak['transaction_count'].idxmax()]
    st.success(f"🔝 Peak Hour: **{day_names[peak_row['day_of_week']]}** at **{peak_row['hour']}:00** with **{int(peak_row['transaction_count']):,}** transactions")
else:
    st.info("No peak hours data available.")

st.markdown("---")

# Store Performance Comparison
st.markdown("## 🏪 Store Performance Comparison")

col1, col2 = st.columns(2)

with col1:
    store_perf_query = f"""
    SELECT
        store_id,
        sum(if(transaction_type = 'SALE', quantity * unit_price, 0)) as total_revenue,
        countIf(transaction_type = 'SALE') as sales_count,
        countIf(transaction_type = 'RETURN') as return_count
    FROM retail_events_unified
    WHERE toDate(event_time) >= today() - INTERVAL {days_back} DAY
    GROUP BY store_id
    ORDER BY total_revenue DESC
    LIMIT 15
    """
    
    df_store_perf = execute_query(store_perf_query)
    
    if df_store_perf is not None and not df_store_perf.empty:
        fig_store = create_bar_chart(
            df_store_perf.head(10),
            x='store_id',
            y='total_revenue',
            title='Top 10 Stores by Revenue',
            height=400
        )
        st.plotly_chart(fig_store, use_container_width=True)

with col2:
    if df_store_perf is not None and not df_store_perf.empty:
        # Calculate return rate
        df_store_perf['return_rate'] = (df_store_perf['return_count'] / 
                                         df_store_perf['sales_count'] * 100).fillna(0)
        
        st.markdown("### Store Metrics")
        st.dataframe(
            df_store_perf.head(10).style.format({
                'total_revenue': lambda x: format_currency(x),
                'sales_count': '{:,.0f}',
                'return_count': '{:,.0f}',
                'return_rate': '{:.1f}%'
            }),
            use_container_width=True,
            hide_index=True
        )

st.markdown("---")

# Return Rate Analysis
st.markdown("## 🔄 Return Rate Analysis")
st.markdown("Products with highest return rates")

return_query = f"""
SELECT
    category,
    product_id,
    countIf(transaction_type = 'SALE') as sales_count,
    countIf(transaction_type = 'RETURN') as return_count,
    return_count / nullIf(sales_count, 0) * 100 as return_rate_pct
FROM retail_events_unified
WHERE toDate(event_time) >= today() - INTERVAL {days_back} DAY
GROUP BY category, product_id
HAVING sales_count > 5
ORDER BY return_rate_pct DESC
LIMIT 20
"""

df_returns = execute_query(return_query)

if df_returns is not None and not df_returns.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_returns = create_bar_chart(
            df_returns.head(10),
            x='product_id',
            y='return_rate_pct',
            title='Top 10 Products by Return Rate',
            height=400
        )
        st.plotly_chart(fig_returns, use_container_width=True)
    
    with col2:
        st.markdown("### Return Details")
        st.dataframe(
            df_returns.head(10).style.format({
                'sales_count': '{:,.0f}',
                'return_count': '{:,.0f}',
                'return_rate_pct': '{:.1f}%'
            }),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No return data available.")

st.markdown("---")

# Category Performance
st.markdown("## 🏷️ Category Performance Breakdown")

category_perf_query = f"""
SELECT
    category,
    count() as total_transactions,
    sum(quantity * unit_price) as total_revenue,
    avg(quantity * unit_price) as avg_transaction_value,
    sum(quantity) as total_items
FROM retail_events_unified
WHERE transaction_type = 'SALE'
    AND toDate(event_time) >= today() - INTERVAL {days_back} DAY
GROUP BY category
ORDER BY total_revenue DESC
"""

df_category_perf = execute_query(category_perf_query)

if df_category_perf is not None and not df_category_perf.empty:
    # Calculate revenue share
    total_rev = df_category_perf['total_revenue'].sum()
    df_category_perf['revenue_share'] = (df_category_perf['total_revenue'] / total_rev * 100)
    
    st.dataframe(
        df_category_perf.style.format({
            'total_transactions': '{:,.0f}',
            'total_revenue': lambda x: format_currency(x),
            'avg_transaction_value': lambda x: format_currency(x),
            'total_items': '{:,.0f}',
            'revenue_share': '{:.1f}%'
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No category performance data available.")

# Footer
st.markdown("---")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
