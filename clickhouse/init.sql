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
