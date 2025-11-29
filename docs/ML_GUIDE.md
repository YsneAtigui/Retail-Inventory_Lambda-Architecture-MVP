# Machine Learning Guide - Demand Forecasting

## Overview

The ML system predicts product demand 7 days ahead using historical sales data and a Random Forest model trained in Spark MLlib.

## Architecture

```
Historical Data → Spark ML Training (Weekly) → Model Storage
                                                     ↓
Features → Spark Prediction (Daily) → ClickHouse → Power BI
```

---

## 🚀 Quick Start

### 1. Initialize ML Tables

```powershell
Get-Content clickhouse/ml_tables.sql | docker exec -i clickhouse clickhouse-client --user=default --password=password123 --multiquery
```

### 2. Train Initial Model

```powershell
# Manual trigger via Airflow
docker exec airflow-webserver airflow dags trigger ml_training

# OR run directly with Spark
docker exec spark-master /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
    /opt/airflow/spark/ml_demand_forecast.py
```

**Training takes**: 5-10 minutes
**Output**: Model saved to MinIO at `s3a://retail-lake/models/`

### 3. Generate Predictions

```powershell
# Trigger daily predictions
docker exec airflow-webserver airflow dags trigger ml_daily_predictions
```

**Output**: 7-day forecasts saved to ClickHouse `demand_predictions` table

---

## 📊 Using Predictions in Power BI

### Connect to Prediction Tables

1. **Open Power BI Desktop**
2. **Get Data → ODBC** (or your existing connection)
3. **Add these tables**:
   - `retail.demand_predictions` - All forecasts
   - `retail.daily_demand_forecast` - Daily summaries
   - `retail.prediction_accuracy` - Accuracy tracking
   - `retail.restock_recommendations` - Business insights

### Example Queries

**Get Next 7 Days Forecast:**
```sql
SELECT 
    forecast_date,
    product_id,
    store_id,
    sum(predicted_demand) as daily_forecast
FROM retail.demand_predictions
WHERE forecast_date BETWEEN today() AND today() + INTERVAL 7 DAY
GROUP BY forecast_date, product_id, store_id
ORDER BY forecast_date, daily_forecast DESC;
```

**Check Model Accuracy:**
```sql
SELECT
    model_version,
    avg_percentage_error,
    median_percentage_error,
    predictions_made
FROM retail.model_performance_summary
ORDER BY model_version DESC
LIMIT 5;
```

**Restock Recommendations:**
```sql
SELECT 
    product_id,
    store_id,
    predicted_demand_7d,
    historical_avg_7d,
    recommendation
FROM retail.restock_recommendations
WHERE recommendation = 'HIGH_DEMAND'
ORDER BY predicted_demand_7d DESC
LIMIT 20;
```

---

## 📈 Dashboard Ideas

### 1. Demand Forecast Dashboard
- **Line Chart**: Predicted vs Actual demand over time
- **Table**: Top 20 products by predicted demand
- **Card**: Total forecasted units next 7 days
- **Map**: Store-level demand heatmap

### 2. Model Performance Dashboard
- **Line Chart**: Model accuracy trend (RMSE, MAE over time)
- **Scatter**: Predicted vs Actual (correlation)
- **Table**: Model versions with metrics

### 3. Inventory Planning Dashboard
- **Table**: Restock recommendations with priority
- **Bar Chart**: Products with highest demand increase
- **KPI Cards**: Stock alerts, high demand products

---

## 🔧 Configuration

### Model Parameters

Edit `spark/ml_demand_forecast.py`:

```python
# Random Forest configuration
rf = RandomForestRegressor(
    numTrees=100,      # More trees = better accuracy, slower training
    maxDepth=10,       # Deeper = more complex patterns
    maxBins=32,        # More bins = better categorical handling
    seed=42
)
```

### Prediction Window

Edit `spark/ml_prediction_batch.py`:

```python
# Change from 7 days to 14 days
features_df = generate_prediction_features(spark, days_ahead=14)
```

### Schedule

Edit Airflow DAGs:

```python
# ml_training_dag.py
schedule_interval='0 2 * * 0',  # Weekly on Sunday 2 AM

# ml_daily_predictions_dag.py  
schedule_interval='0 1 * * *',  # Daily at 1 AM
```

---

## 🧪 Testing & Validation

### Check Model Metrics

```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT * FROM retail.model_metrics ORDER BY training_date DESC LIMIT 1" --format=Pretty
```

### View Sample Predictions

```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT product_id, forecast_date, predicted_demand FROM retail.demand_predictions LIMIT 10" --format=Pretty
```

### Compare Accuracy

```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT avg(percentage_error) as avg_error FROM retail.prediction_accuracy WHERE forecast_date >= today() - 7" --format=Pretty
```

---

## 🛠️ Troubleshooting

### "Model not found"
```powershell
# Check if model exists
docker exec spark-master ls -la /opt/spark/work/models/
```

### "No predictions generated"
```powershell
# Check Spark logs
docker logs spark-master --tail 100

# Check Airflow task logs
# Go to http://localhost:8081 → DAGs → ml_daily_predictions → Logs
```

### "Poor accuracy (>30% error)"
- **Train with more data**: Ensure you have at least 3 months of historical data
- **Tune hyperparameters**: Increase `numTrees` or `maxDepth`
- **Add more features**: Include promotions, holidays, weather

---

## 📝 Model Features

The model uses these features to predict demand:

**Product Features:**
- `product_id` - Which product
- `store_id` - Which store location

**Time Features:**
- `day_of_week` - 1-7 (1=Monday)
- `hour_of_day` - 0-23
- `month` - 1-12
- `is_weekend` - Boolean
- `is_holiday_season` - Nov-Dec flag
- `is_summer` - Jun-Aug flag

**Historical Features:**
- `avg_demand` - Historical average for this product/store/day
- `transaction_count` - Historical transaction frequency

---

## 🎯 Next Steps

1. **Monitor weekly**: Check model accuracy in Power BI
2. **Retrain regularly**: Schedule stays weekly on Sundays
3. **Add features**: Include promotions, competitor pricing, weather
4. **A/B test**: Compare multiple models (GBT vs Random Forest)
5. **Automate actions**: Trigger restock orders based on predictions

---

## 📚 Files Reference

- **Training**: `spark/ml_demand_forecast.py`
- **Prediction**: `spark/ml_prediction_batch.py`
- **DAGs**: `airflow/dags/ml_*.py`
- **Tables**: `clickhouse/ml_tables.sql`
- **Models**: Stored in MinIO `retail-lake/models/`

---

**Need help?** Check Airflow logs at http://localhost:8081 or Spark logs with `docker logs spark-master`
