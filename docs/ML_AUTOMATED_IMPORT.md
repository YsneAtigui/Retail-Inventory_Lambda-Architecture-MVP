# Automated Prediction Import - Setup Complete! ✅

## What Was Implemented

Both ML DAGs now automatically import predictions to ClickHouse after generation.

### Updated DAGs

**1. `ml_training_dag.py`** (Weekly - Sundays 2 AM)
```
train_model → generate_predictions → import_to_clickhouse
```

**2. `ml_daily_predictions_dag.py`** (Daily - 1 AM)
```
generate_predictions → import_to_clickhouse
```

## How It Works

After predictions are generated and saved to MinIO as Parquet files, the `import_to_clickhouse` task automatically:

1. **Reads predictions from MinIO** using ClickHouse S3 table function
2. **Filters recent predictions** (last 2 hours) to avoid duplicates
3. **Inserts into** `retail.demand_predictions` table

## Import Query

The DAGs use this query:
```sql
INSERT INTO retail.demand_predictions 
SELECT 
    toString(prediction_id) as prediction_id,
    prediction_time,
    model_version,
    product_id,
    store_id,
    forecast_date,
    forecast_hour,
    predicted_demand,
    confidence_lower,
    confidence_upper,
    day_of_week,
    month,
    is_weekend,
    seasonal_factor
FROM s3(
    'http://minio:9000/retail-lake/predictions/*/part-*.parquet',
    'minioadmin',
    'minioadmin',
    'Parquet'
)
WHERE prediction_time >= now() - INTERVAL 2 HOUR
```

## Verify Import

After running a DAG, check the data:

```powershell
# Count predictions
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.demand_predictions" --format=Pretty

# View latest predictions
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT product_id, forecast_date, predicted_demand FROM retail.demand_predictions ORDER BY prediction_time DESC LIMIT 10" --format=Pretty

# Check by model version
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT model_version, count() as predictions, min(forecast_date), max(forecast_date) FROM retail.demand_predictions GROUP BY model_version" --format=Pretty
```

## Manual Import (If Needed)

To manually import all predictions from MinIO:

```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="
INSERT INTO retail.demand_predictions 
SELECT 
    toString(prediction_id) as prediction_id,
    prediction_time,
    model_version,
    product_id,
    store_id,
    forecast_date,
    forecast_hour,
    predicted_demand,
    confidence_lower,
    confidence_upper,
    day_of_week,
    month,
    is_weekend,
    seasonal_factor
FROM s3(
    'http://minio:9000/retail-lake/predictions/*/part-*.parquet',
    'minioadmin',
    'minioadmin',
    'Parquet'
)
"
```

## Test the Complete Flow

Trigger the DAG and watch all 3 tasks execute:

```powershell
docker exec airflow-webserver airflow dags trigger ml_daily_predictions

# Then monitor in Airflow UI: http://localhost:8081
```

You should see:
1. ✅ `generate_7day_forecast` - Creates predictions in MinIO
2. ✅ `import_predictions_to_clickhouse` - Loads into ClickHouse
3. ✅ Predictions ready for Power BI!

## Benefits

- 🔄 **Fully automated** - No manual imports needed
- ⚡ **Fast** - Direct S3→ClickHouse using Parquet
- 🛡️ **No duplicates** - Time filter prevents re-importing
- 📊 **Power BI ready** - Data immediately available for dashboards

---

**Now your ML pipeline is 100% automated from training to serving!** 🎉
