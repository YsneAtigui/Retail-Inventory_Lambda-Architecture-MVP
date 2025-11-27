-- Machine Learning Tables for Demand Forecasting
-- Add this to your ClickHouse initialization

USE retail;

-- ========================================
-- ML PREDICTIONS TABLES
-- ========================================

-- Store demand predictions
CREATE TABLE IF NOT EXISTS demand_predictions (
    prediction_id UUID DEFAULT generateUUIDv4(),
    prediction_time DateTime DEFAULT now(),
    model_version String,
    
    -- Prediction target
    product_id String,
    store_id Int32,
    forecast_date Date,
    forecast_hour Int32,
    
    -- Prediction values
    predicted_demand Float64,
    confidence_lower Float64,
    confidence_upper Float64,
    
    -- Features used
    day_of_week Int32,
    month Int32,
    is_weekend UInt8,
    seasonal_factor Float64,
    
    -- Metadata
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(forecast_date)
ORDER BY (forecast_date, product_id, store_id, forecast_hour);

-- Track model performance metrics
CREATE TABLE IF NOT EXISTS model_metrics (
    metric_id UUID DEFAULT generateUUIDv4(),
    model_version String,
    model_type String DEFAULT 'demand_forecast',
    
    -- Training metrics
    training_date DateTime,
    training_samples Int64,
    
    -- Performance metrics
    rmse Float64,
    mae Float64,
    r2_score Float64,
    
    -- Model parameters
    parameters String,  -- JSON string
    
    -- Status
    is_active UInt8 DEFAULT 0,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (model_type, training_date);

-- Track prediction accuracy (compare predictions vs actual)
CREATE VIEW IF NOT EXISTS prediction_accuracy AS
SELECT
    p.product_id,
    p.store_id,
    p.forecast_date,
    p.forecast_hour,
    p.predicted_demand,
    a.actual_demand,
    abs(p.predicted_demand - a.actual_demand) as absolute_error,
    (abs(p.predicted_demand - a.actual_demand) / nullIf(a.actual_demand, 0)) * 100 as percentage_error,
    p.model_version,
    p.prediction_time
FROM demand_predictions p
LEFT JOIN (
    SELECT 
        product_id,
        store_id,
        toDate(event_time) as date,
        toHour(event_time) as hour,
        sum(quantity) as actual_demand
    FROM retail_events_realtime
    WHERE transaction_type = 'SALE'
    GROUP BY product_id, store_id, date, hour
) a ON p.product_id = a.product_id 
   AND p.store_id = a.store_id 
   AND p.forecast_date = a.date
   AND p.forecast_hour = a.hour
WHERE a.actual_demand IS NOT NULL;

-- Summary of model performance
CREATE VIEW IF NOT EXISTS model_performance_summary AS
SELECT
    model_version,
    count() as predictions_made,
    countIf(actual_demand IS NOT NULL) as predictions_with_actual,
    avg(absolute_error) as avg_absolute_error,
    avg(percentage_error) as avg_percentage_error,
    quantile(0.5)(percentage_error) as median_percentage_error,
    quantile(0.9)(percentage_error) as p90_percentage_error
FROM prediction_accuracy
GROUP BY model_version
ORDER BY model_version DESC;

-- Daily forecast summary for Power BI
CREATE VIEW IF NOT EXISTS daily_demand_forecast AS
SELECT
    forecast_date,
    product_id,
    store_id,
    sum(predicted_demand) as total_daily_demand,
    min(predicted_demand) as min_hourly_demand,
    max(predicted_demand) as max_hourly_demand,
    avg(predicted_demand) as avg_hourly_demand,
    model_version,
    max(prediction_time) as latest_prediction_time
FROM demand_predictions
WHERE forecast_date >= today()
GROUP BY forecast_date, product_id, store_id, model_version
ORDER BY forecast_date ASC, total_daily_demand DESC;

-- Top products needing restock (low predicted demand vs historical)
CREATE VIEW IF NOT EXISTS restock_recommendations AS
SELECT
    p.product_id,
    p.store_id,
    p.forecast_date,
    sum(p.predicted_demand) as predicted_demand_7d,
    avg(h.historical_avg) as historical_avg_7d,
    (sum(p.predicted_demand) / nullIf(avg(h.historical_avg), 0)) as demand_ratio,
    CASE
        WHEN demand_ratio > 1.5 THEN 'HIGH_DEMAND'
        WHEN demand_ratio > 1.2 THEN 'MODERATE_INCREASE'
        WHEN demand_ratio < 0.8 THEN 'LOW_DEMAND'
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
GROUP BY p.product_id, p.store_id, p.forecast_date
HAVING predicted_demand_7d > 0
ORDER BY demand_ratio DESC;
