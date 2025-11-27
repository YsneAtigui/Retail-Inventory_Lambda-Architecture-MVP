-- Create database
CREATE DATABASE IF NOT EXISTS retail;

USE retail;

-- ========================================
-- REAL-TIME LAYER (Speed Layer)
-- ========================================

-- Kafka Engine Table: Consumes messages from Kafka topic
CREATE TABLE IF NOT EXISTS retail_events_kafka (
    event_time String,
    store_id Int32,
    product_id String,
    category String,
    transaction_type String,
    quantity Int32,
    unit_price Float64
) ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka:29092',
    kafka_topic_list = 'retail_events',
    kafka_group_name = 'clickhouse_consumer',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

-- Real-time MergeTree Table: Stores the data
CREATE TABLE IF NOT EXISTS retail_events_realtime (
    event_time DateTime,
    store_id Int32,
    product_id String,
    category String,
    transaction_type String,
    quantity Int32,
    unit_price Float64,
    inserted_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_time, store_id, product_id);

-- Materialized View: Automatically moves data from Kafka to MergeTree
CREATE MATERIALIZED VIEW IF NOT EXISTS retail_events_mv TO retail_events_realtime AS
SELECT
    parseDateTime64BestEffort(event_time) AS event_time,
    store_id,
    product_id,
    category,
    transaction_type,
    quantity,
    unit_price
FROM retail_events_kafka;

-- ========================================
-- BATCH LAYER (Historical Data)
-- ========================================

-- S3 Engine Table: Reads Parquet files from MinIO
CREATE TABLE IF NOT EXISTS retail_events_historical (
    event_time DateTime,
    store_id Int32,
    product_id String,
    category String,
    transaction_type String,
    quantity Int32,
    unit_price Float64
) ENGINE = S3(
    'http://minio:9000/retail-lake/*.parquet',
    'minioadmin',
    'minioadmin',
    'Parquet'
);

-- ========================================
-- SERVING LAYER (Unified View)
-- ========================================

-- Unified View: Combines real-time and historical data
CREATE VIEW IF NOT EXISTS retail_events_unified AS
SELECT
    event_time,
    store_id,
    product_id,
    category,
    transaction_type,
    quantity,
    unit_price,
    'realtime' AS source
FROM retail_events_realtime

UNION ALL

SELECT
    event_time,
    store_id,
    product_id,
    category,
    transaction_type,
    quantity,
    unit_price,
    'historical' AS source
FROM retail_events_historical;

-- ========================================
-- AGGREGATION VIEWS FOR POWER BI
-- ========================================

-- Sales by Category
CREATE VIEW IF NOT EXISTS sales_by_category AS
SELECT
    category,
    transaction_type,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_quantity,
    SUM(quantity * unit_price) AS total_revenue,
    AVG(unit_price) AS avg_unit_price
FROM retail_events_unified
WHERE transaction_type = 'SALE'
GROUP BY category, transaction_type;

-- Sales by Store
CREATE VIEW IF NOT EXISTS sales_by_store AS
SELECT
    store_id,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_quantity,
    SUM(quantity * unit_price) AS total_revenue
FROM retail_events_unified
WHERE transaction_type = 'SALE'
GROUP BY store_id;

-- Hourly Sales Trend
CREATE VIEW IF NOT EXISTS hourly_sales_trend AS
SELECT
    toStartOfHour(event_time) AS hour,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_quantity,
    SUM(quantity * unit_price) AS total_revenue
FROM retail_events_unified
WHERE transaction_type = 'SALE'
GROUP BY hour
ORDER BY hour DESC;

-- Product Performance
CREATE VIEW IF NOT EXISTS product_performance AS
SELECT
    product_id,
    category,
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_quantity,
    SUM(quantity * unit_price) AS total_revenue,
    AVG(unit_price) AS avg_unit_price
FROM retail_events_unified
WHERE transaction_type = 'SALE'
GROUP BY product_id, category
ORDER BY total_revenue DESC;

-- ========================================
-- PERFORMANCE ENHANCEMENTS
-- ========================================

-- 1. Add TTL to real-time table (keep only 90 days)
ALTER TABLE retail_events_realtime 
MODIFY TTL event_time + INTERVAL 90 DAY;

-- 2. Create daily sales summary materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_sales_summary
ENGINE = SummingMergeTree()
ORDER BY (date, store_id, category)
AS SELECT
    toDate(event_time) as date,
    store_id,
    category,
    transaction_type,
    count() as transaction_count,
    sum(quantity) as total_quantity,
    sum(quantity * unit_price) as total_revenue
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
GROUP BY date, store_id, category, transaction_type;

-- 3. Create hourly sales summary for real-time monitoring
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_sales_summary
ENGINE = SummingMergeTree()
ORDER BY (hour, store_id, category)
AS SELECT
    toStartOfHour(event_time) as hour,
    store_id,
    category,
    count() as transaction_count,
    sum(quantity) as total_quantity,
    sum(quantity * unit_price) as total_revenue
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
GROUP BY hour, store_id, category;

-- 4. Create product performance summary
CREATE MATERIALIZED VIEW IF NOT EXISTS product_performance_summary
ENGINE = SummingMergeTree()
ORDER BY (product_id, category, transaction_type)
AS SELECT
    product_id,
    category,
    transaction_type,
    count() as transaction_count,
    sum(quantity) as total_quantity,
    sum(quantity * unit_price) as total_revenue,
    avg(unit_price) as avg_unit_price
FROM retail_events_realtime
GROUP BY product_id, category, transaction_type;

-- ========================================
-- ADVANCED ANALYTICAL VIEWS
-- ========================================

-- 5. Create anomaly detection view
CREATE VIEW IF NOT EXISTS sales_anomaly_detection AS
SELECT 
    category,
    toStartOfHour(event_time) as hour,
    sum(quantity * unit_price) as hourly_revenue,
    avg(sum(quantity * unit_price)) OVER (PARTITION BY category ORDER BY toStartOfHour(event_time) ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) as moving_avg_24h,
    stddevPop(sum(quantity * unit_price)) OVER (PARTITION BY category ORDER BY toStartOfHour(event_time) ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) as std_dev_24h
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
  AND event_time >= now() - INTERVAL 7 DAY
GROUP BY category, hour
ORDER BY hour DESC;

-- 6. Create return rate analysis view
CREATE VIEW IF NOT EXISTS return_rate_analysis AS
SELECT 
    category,
    product_id,
    countIf(transaction_type = 'SALE') as sales_count,
    countIf(transaction_type = 'RETURN') as return_count,
    return_count / nullIf(sales_count, 0) * 100 as return_rate_pct,
    sum(if(transaction_type = 'SALE', quantity * unit_price, 0)) as total_sales_revenue,
    sum(if(transaction_type = 'RETURN', quantity * unit_price, 0)) as total_return_value
FROM retail_events_unified
GROUP BY category, product_id
HAVING sales_count > 0
ORDER BY return_rate_pct DESC;

-- 7. Create store performance comparison view
CREATE VIEW IF NOT EXISTS store_performance_comparison AS
SELECT 
    store_id,
    toDate(event_time) as date,
    countIf(transaction_type = 'SALE') as sales_transactions,
    countIf(transaction_type = 'RETURN') as return_transactions,
    sum(if(transaction_type = 'SALE', quantity * unit_price, 0)) as daily_revenue,
    avg(if(transaction_type = 'SALE', quantity * unit_price, 0)) as avg_transaction_value,
    sum(quantity) as total_items_moved
FROM retail_events_unified
WHERE toDate(event_time) >= today() - INTERVAL 30 DAY
GROUP BY store_id, date
ORDER BY date DESC, daily_revenue DESC;

-- 8. Create peak hours identification view
CREATE VIEW IF NOT EXISTS peak_hours_by_day AS
SELECT 
    toDayOfWeek(event_time) as day_of_week,
    toHour(event_time) as hour,
    count() as transaction_count,
    sum(quantity * unit_price) as revenue,
    avg(quantity * unit_price) as avg_basket_value
FROM retail_events_unified
WHERE transaction_type = 'SALE'
  AND toDate(event_time) >= today() - INTERVAL 30 DAY
GROUP BY day_of_week, hour
ORDER BY transaction_count DESC;
