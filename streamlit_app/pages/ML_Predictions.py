"""
ML Predictions Dashboard
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
from utils.charts import create_line_chart, create_scatter_chart, create_bar_chart

# Page configuration
st.set_page_config(
    page_title="ML Predictions | Retail Analytics",
    page_icon="🤖",
    layout="wide"
)

# Title
st.title("🤖 Machine Learning Predictions Dashboard")
st.markdown("### Demand forecasting and model performance analytics")

# Check if ML tables exist
check_query = """
SELECT count() as count 
FROM demand_predictions
"""
df_check = execute_query(check_query)

if df_check is None or df_check.empty or df_check['count'].iloc[0] == 0:
    st.warning("⚠️ No ML prediction data available yet. Please ensure the ML pipeline has run.")
    st.info("""
    **To generate predictions:**
    1. Ensure Airflow is running
    2. Trigger the ML training DAG
    3. Wait for predictions to be imported to ClickHouse
    
    See ML_GUIDE.md and ML_AUTOMATED_IMPORT.md for details.
    """)
    st.stop()

st.markdown("---")

# Model Performance Metrics
st.markdown("## 📊 Model Performance Overview")

model_metrics_query = """
SELECT
    model_version,
    rmse,
    mae,
    r2_score,
    training_samples,
    training_date
FROM model_metrics
WHERE is_active = 1
ORDER BY training_date DESC
LIMIT 1
"""

df_model = execute_query(model_metrics_query)

if df_model is not None and not df_model.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📈 R² Score",
            value=f"{df_model['r2_score'].iloc[0]:.4f}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="📉 RMSE",
            value=f"{df_model['rmse'].iloc[0]:.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="📊 MAE",
            value=f"{df_model['mae'].iloc[0]:.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            label="🎓 Training Samples",
            value=format_number(df_model['training_samples'].iloc[0]),
            delta=None
        )
    
    st.info(f"🤖 **Active Model:** {df_model['model_version'].iloc[0]} | **Trained:** {df_model['training_date'].iloc[0]}")
else:
    st.info("No model metrics available.")

st.markdown("---")

# Demand Forecast
st.markdown("## 📅 7-Day Demand Forecast")

# Product and Store filters
col1, col2 = st.columns(2)

with col1:
    # Get unique products
    products_query = """
    SELECT DISTINCT product_id 
    FROM demand_predictions 
    ORDER BY product_id
    LIMIT 50
    """
    df_products = execute_query(products_query)
    
    if df_products is not None and not df_products.empty:
        selected_product = st.selectbox(
            "Select Product",
            options=['All'] + df_products['product_id'].tolist()
        )
    else:
        selected_product = 'All'

with col2:
    # Get unique stores
    stores_query = """
    SELECT DISTINCT store_id 
    FROM demand_predictions 
    ORDER BY store_id
    LIMIT 20
    """
    df_stores = execute_query(stores_query)
    
    if df_stores is not None and not df_stores.empty:
        selected_store = st.selectbox(
            "Select Store",
            options=['All'] + [int(x) for x in df_stores['store_id'].tolist()]
        )
    else:
        selected_store = 'All'

# Build forecast query with filters
forecast_query = """
SELECT
    forecast_date,
    sum(predicted_demand) as total_demand,
    avg(confidence_lower) as avg_lower,
    avg(confidence_upper) as avg_upper,
    count() as product_count
FROM demand_predictions
WHERE forecast_date >= today()
    AND forecast_date <= today() + INTERVAL 7 DAY
"""

if selected_product != 'All':
    forecast_query += f" AND product_id = '{selected_product}'"
if selected_store != 'All':
    forecast_query += f" AND store_id = {selected_store}"

forecast_query += """
GROUP BY forecast_date
ORDER BY forecast_date ASC
"""

df_forecast = execute_query(forecast_query)

if df_forecast is not None and not df_forecast.empty:
    fig_forecast = create_line_chart(
        df_forecast,
        x='forecast_date',
        y='total_demand',
        title='Predicted Demand (Next 7 Days)',
        height=400
    )
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    # Summary
    total_forecast = df_forecast['total_demand'].sum()
    avg_daily = df_forecast['total_demand'].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Forecasted Demand", f"{total_forecast:.0f} units")
    with col2:
        st.metric("Avg Daily Demand", f"{avg_daily:.0f} units")
else:
    st.info("No forecast data available for the selected filters.")

st.markdown("---")

# Prediction Accuracy
st.markdown("## 🎯 Prediction Accuracy Analysis")

accuracy_query = """
SELECT
    product_id,
    avg(predicted_demand) as avg_predicted,
    avg(actual_demand) as avg_actual,
    avg(absolute_error) as avg_error,
    avg(percentage_error) as avg_pct_error,
    count() as sample_count
FROM prediction_accuracy
GROUP BY product_id
HAVING sample_count >= 3
ORDER BY avg_pct_error ASC
LIMIT 20
"""

df_accuracy = execute_query(accuracy_query)

if df_accuracy is not None and not df_accuracy.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_accuracy = create_scatter_chart(
            df_accuracy,
            x='avg_actual',
            y='avg_predicted',
            title='Predicted vs Actual Demand',
            height=400
        )
        # Add perfect prediction line
        fig_accuracy.add_shape(
            type="line",
            x0=0, y0=0,
            x1=df_accuracy['avg_actual'].max(),
            y1=df_accuracy['avg_actual'].max(),
            line=dict(color="red", width=2, dash="dash")
        )
        st.plotly_chart(fig_accuracy, use_container_width=True)
    
    with col2:
        st.markdown("### Accuracy by Product")
        st.dataframe(
            df_accuracy.head(10).style.format({
                'avg_predicted': '{:.1f}',
                'avg_actual': '{:.1f}',
                'avg_error': '{:.1f}',
                'avg_pct_error': '{:.1f}%',
                'sample_count': '{:.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No prediction accuracy data available yet. Predictions need actual data to compare against.")

st.markdown("---")

# Restock Recommendations
st.markdown("## 📦 Restock Recommendations")

restock_query = """
SELECT
    p.product_id,
    p.store_id,
    sum(p.predicted_demand) as predicted_7d,
    CASE
        WHEN sum(p.predicted_demand) / nullIf(avg(h.historical_avg), 0) > 1.5 THEN 'HIGH_DEMAND'
        WHEN sum(p.predicted_demand) / nullIf(avg(h.historical_avg), 0) > 1.2 THEN 'MODERATE_INCREASE'
        WHEN sum(p.predicted_demand) / nullIf(avg(h.historical_avg), 0) < 0.8 THEN 'LOW_DEMAND'
        ELSE 'NORMAL'
    END as recommendation
FROM demand_predictions p
LEFT JOIN (
    SELECT
        product_id,
        store_id,
        avg(quantity) as historical_avg
    FROM retail_events_realtime
    WHERE transaction_type = 'SALE'
      AND event_time >= now() - INTERVAL 30 DAY
    GROUP BY product_id, store_id
) h ON p.product_id = h.product_id AND p.store_id = h.store_id
WHERE p.forecast_date BETWEEN today() AND today() + INTERVAL 7 DAY
GROUP BY p.product_id, p.store_id
HAVING predicted_7d > 0
ORDER BY predicted_7d DESC
LIMIT 30
"""

df_restock = execute_query(restock_query)

if df_restock is not None and not df_restock.empty:
    # Filter by recommendation
    filter_rec = st.multiselect(
        "Filter by Recommendation",
        options=['HIGH_DEMAND', 'MODERATE_INCREASE', 'NORMAL', 'LOW_DEMAND'],
        default=['HIGH_DEMAND', 'MODERATE_INCREASE']
    )
    
    if filter_rec:
        df_filtered = df_restock[df_restock['recommendation'].isin(filter_rec)]
    else:
        df_filtered = df_restock
    
    # Color coding for recommendations
    def color_recommendation(val):
        if val == 'HIGH_DEMAND':
            return 'background-color: #e74c3c; color: white'
        elif val == 'MODERATE_INCREASE':
            return 'background-color: #f39c12; color: white'
        elif val == 'LOW_DEMAND':
            return 'background-color: #3498db; color: white'
        else:
            return 'background-color: #95a5a6; color: white'
    
    st.dataframe(
        df_filtered.head(20).style.format({
            'predicted_7d': '{:.0f}'
        }).applymap(color_recommendation, subset=['recommendation']),
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    st.success(f"📊 Showing {len(df_filtered)} recommendations")
else:
    st.info("No restock recommendations available.")

# Footer
st.markdown("---")
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
