# Lambda Architecture - Data Flow Documentation

## Architecture Overview

This project implements a **Lambda Architecture** for real-time and batch processing of retail inventory data. The architecture consists of three main layers:

1. **Speed Layer** (Real-time processing)
2. **Batch Layer** (Historical processing)
3. **Serving Layer** (Query interface)

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│                  (Python Producer with Faker)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   Apache Kafka        │
              │   Topic: retail_events│
              └──────────┬────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────┐
│  SPEED LAYER  │ │ BATCH LAYER  │ │ ORCHESTRATION│
│  (Real-time)  │ │ (Historical) │ │  (Airflow)  │
└───────┬───────┘ └──────┬───────┘ └──────┬──────┘
        │                │                 │
        ▼                ▼                 ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│  ClickHouse   │ │    Spark     │ │   Schedule   │
│  Kafka Engine │ │  Processor   │ │   DAG Runs   │
└───────┬───────┘ └──────┬───────┘ └──────────────┘
        │                │
        ▼                ▼
┌───────────────┐ ┌──────────────┐
│  MergeTree    │ │    MinIO     │
│   Table       │ │ (Data Lake)  │
└───────┬───────┘ └──────┬───────┘
        │                │
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │ SERVING LAYER  │
        │   ClickHouse   │
        │  Unified View  │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │   Power BI     │
        │  Dashboards    │
        └────────────────┘
```

---

## Data Schema

All events follow this JSON structure:

```json
{
  "event_time": "2025-11-27 16:00:00",
  "store_id": 1,
  "product_id": "Laptop",
  "category": "Electronics",
  "transaction_type": "SALE",
  "quantity": 5,
  "unit_price": 450.00
}
```

**Field Descriptions:**
- `event_time`: Timestamp of the transaction (YYYY-MM-DD HH:MM:SS)
- `store_id`: Store identifier (1-10)
- `product_id`: Product name (e.g., Laptop, T-Shirt, Coffee Maker)
- `category`: Product category (Electronics, Clothing, Home, Books, Sports)
- `transaction_type`: Type of transaction (SALE, RETURN, RESTOCK)
- `quantity`: Number of items in transaction
- `unit_price`: Price per unit in dollars

---

## Layer 1: Speed Layer (Real-Time Processing)

### Purpose
Handle real-time data streaming for immediate insights.

### Data Flow

```
Producer → Kafka → ClickHouse Kafka Engine → MergeTree Table
```

### Step-by-Step Process

#### 1. **Data Generation** (Producer)
- **Component**: Python script with Faker library
- **Location**: `producer/main.py`
- **Frequency**: 2 events per second
- **Output**: JSON events to Kafka

```python
# Producer generates events like:
{
  "event_time": "2025-11-27 16:00:00",
  "store_id": 5,
  "product_id": "Laptop",
  "category": "Electronics",
  "transaction_type": "SALE",
  "quantity": 3,
  "unit_price": 1200.00
}
```

#### 2. **Message Broker** (Kafka)
- **Topic**: `retail_events`
- **Port**: 9092 (external), 29092 (internal)
- **Partitions**: 1
- **Replication**: 1
- **Function**: Buffer and distribute events

#### 3. **Real-Time Consumption** (ClickHouse Kafka Engine)
- **Table**: `retail_events_kafka`
- **Engine**: Kafka Engine
- **Configuration**:
  - Broker: `kafka:29092`
  - Topic: `retail_events`
  - Format: `JSONEachRow`
  - Consumer Group: `clickhouse_consumer`

```sql
-- Kafka Engine Table (virtual, continuously reads from Kafka)
CREATE TABLE retail_events_kafka (
    event_time String,
    store_id Int32,
    product_id String,
    category String,
    transaction_type String,
    quantity Int32,
    unit_price Float64
) ENGINE = Kafka()
SETTINGS kafka_broker_list = 'kafka:29092', ...
```

#### 4. **Materialized View** (Data Transfer)
- **View**: `retail_events_mv`
- **Function**: Automatically transforms and inserts data
- **Transformation**: Converts `event_time` from String to DateTime

```sql
-- Materialized View (automatically populates MergeTree)
CREATE MATERIALIZED VIEW retail_events_mv TO retail_events_realtime AS
SELECT
    parseDateTime64BestEffort(event_time) AS event_time,
    store_id,
    product_id,
    category,
    transaction_type,
    quantity,
    unit_price
FROM retail_events_kafka;
```

#### 5. **Storage** (MergeTree Table)
- **Table**: `retail_events_realtime`
- **Engine**: MergeTree
- **Partitioning**: By month (`toYYYYMM(event_time)`)
- **Ordering**: By `(event_time, store_id, product_id)`
- **Data Retention**: Real-time and recent data

```sql
CREATE TABLE retail_events_realtime (
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
```

**Current Status**: ✅ **2,363+ events** stored in real-time

---

## Layer 2: Batch Layer (Historical Processing)

### Purpose
Process historical data in batches for long-term storage and analysis.

### Data Flow

```
Kafka → Spark Streaming → MinIO (Parquet) → ClickHouse S3 Engine
```

### Step-by-Step Process

#### 1. **Batch Processing** (Apache Spark)
- **Component**: PySpark streaming job
- **Location**: `spark/batch_processor.py`
- **Trigger**: Manual or Daily (via Airflow DAG)
- **Function**: Read from Kafka, enrich, validate, partition, write to MinIO

**Data Enrichment:**
```python
# Spark automatically adds:
- revenue = quantity * unit_price
- year, month, day (from event_time)
- hour_of_day (0-23)
- day_of_week (1-7, 1=Sunday)
- is_weekend (boolean)
```

**Data Validation:**
- Filters out quantity <= 0
- Filters out unit_price <= 0
- Ensures data quality

**Partitioning Strategy:**
```python
# Partition by date for efficient queries
.partitionBy("year", "month", "day")
.parquet("s3a://retail-lake/")
```

#### 2. **Data Lake Storage** (MinIO)
- **Bucket**: `retail-lake`
- **Format**: Parquet (columnar, compressed)
- **Path Structure**: `s3a://retail-lake/year=2025/month=11/day=27/*.parquet`
- **S3 Endpoint**: `http://minio:9000`
- **Credentials**: `minioadmin/minioadmin`

**Parquet Advantages**:
- Columnar storage (better for analytics)
- High compression ratio
- Partitioned by date for fast range queries

#### 3. **Historical Table** (ClickHouse S3 Engine)
- **Table**: `retail_events_historical`
- **Engine**: S3 (reads directly from MinIO)
- **Function**: Query Parquet files without importing

```sql
CREATE TABLE retail_events_historical (
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
```

---

## Layer 3: Serving Layer

### Purpose
Provide unified query interface combining real-time and historical data.

### Unified View

```sql
CREATE VIEW retail_events_unified AS
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
```

### Pre-Aggregated Views for Performance

ClickHouse includes materialized views that auto-update as new data arrives, providing instant query results.

#### 1. **Daily Sales Summary** (Materialized View)
```sql
CREATE MATERIALIZED VIEW daily_sales_summary
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
```
**Use Case**: Historical dashboards, daily reports (50-100x faster than raw data)

#### 2. **Hourly Sales Summary** (Materialized View)
```sql
CREATE MATERIALIZED VIEW hourly_sales_summary
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
```
**Use Case**: Real-time dashboards, live monitoring

#### 3. **Sales Anomaly Detection** (Analytical View)
```sql
CREATE VIEW sales_anomaly_detection AS
SELECT 
    category,
    toStartOfHour(event_time) as hour,
    sum(quantity * unit_price) as hourly_revenue,
    avg(sum(quantity * unit_price)) OVER (...) as moving_avg_24h,
    stddevPop(sum(quantity * unit_price)) OVER (...) as std_dev_24h
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
GROUP BY category, hour;
```
**Use Case**: Detect unusual sales patterns, automated alerts

#### 4. **Return Rate Analysis** (Analytical View)
```sql
CREATE VIEW return_rate_analysis AS
SELECT 
    category,
    product_id,
    countIf(transaction_type = 'SALE') as sales_count,
    countIf(transaction_type = 'RETURN') as return_count,
    return_count / nullIf(sales_count, 0) * 100 as return_rate_pct
FROM retail_events_unified
GROUP BY category, product_id;
```
**Use Case**: Quality control, identify problematic products

---

## Orchestration (Apache Airflow)

### Purpose
Schedule and monitor batch processing jobs.

### DAG Configuration

- **DAG Name**: `retail_batch_processing`
- **Schedule**: `@daily` (runs once per day)
- **Owner**: airflow
- **Retry**: 1 time with 5-minute delay

### DAG Task Flow

```
┌──────────────────────────────────┐
│  Trigger: Daily at midnight      │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Task: process_retail_events     │
│  Executor: BashOperator          │
│  Command: docker exec spark-submit│
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Spark Job Execution             │
│  - Read from Kafka               │
│  - Transform data                │
│  - Write to MinIO (Parquet)      │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│  Success: Data in MinIO          │
│  Available via S3 Engine         │
└──────────────────────────────────┘
```

**Access Airflow UI**: http://localhost:8081 (admin/admin)

---

## Visualization (Power BI)

### Connection Configuration

**Method 1: ODBC**
- Host: `localhost`
- Port: `8123`
- Database: `retail`
- User: `default`
- Password: `password123`

**Method 2: HTTP/Web**
- URL: `http://localhost:8123/?user=default&password=password123&query=SELECT * FROM retail.retail_events_unified FORMAT JSON`

### Recommended Queries for Dashboards

1. **Real-Time Metrics** (use `retail_events_realtime`)
   - Total transactions today
   - Current revenue
   - Top products this hour

2. **Historical Analysis** (use `retail_events_historical`)
   - Month-over-month trends
   - Seasonal patterns
   - Long-term product performance

3. **Unified Analysis** (use `retail_events_unified` or pre-aggregated views)
   - Complete transaction history
   - Cross-time comparisons
   - Comprehensive reports

---

## Data Lifecycle Summary

| Stage | Component | Storage | Latency | Use Case |
|-------|-----------|---------|---------|----------|
| **Generation** | Python Producer | In-memory | < 1s | Event creation |
| **Streaming** | Apache Kafka | Disk buffer | < 2s | Message queue |
| **Real-time** | ClickHouse Kafka Engine → MergeTree | ClickHouse | < 5s | Live dashboards |
| **Batch** | Spark → MinIO | Parquet files | Daily | Historical analysis |
| **Historical** | ClickHouse S3 Engine | MinIO (S3) | Minutes | Archive queries |
| **Serving** | ClickHouse Unified View | Virtual | < 1s | BI tools |
| **Visualization** | Power BI | Client cache | < 2s | User dashboards |

---

## Performance Characteristics

### Current Metrics (Live System)

- **Event Rate**: 2 events/second
- **Real-time Events**: 2,363+ and growing
- **Event Size**: ~200 bytes per event (JSON)
- **Daily Volume**: ~172,800 events/day
- **Storage (Real-time)**: ~34 MB/day (before compression)
- **Storage (Batch)**: ~10 MB/day (Parquet compressed)

### Query Performance

- **Real-time queries**: < 100ms (MergeTree optimized)
- **Historical queries**: < 500ms (Parquet scanning)
- **Unified queries**: < 1s (union of both sources)
- **Aggregation views**: < 50ms (pre-computed)

---

## Monitoring & Health Checks

### Service Health Endpoints

```bash
# Kafka
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# ClickHouse
curl http://localhost:8123/ping

# MinIO
curl http://localhost:9000/minio/health/live

# Spark
curl http://localhost:8090

# Airflow
curl http://localhost:8081/health
```

### Data Flow Verification

```bash
# Check producer logs
docker logs -f inventory-producer

# Check Kafka messages
docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --max-messages 5

# Check ClickHouse real-time data
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.retail_events_realtime"

# Check MinIO buckets
# Visit: http://localhost:9001 (minioadmin/minioadmin)
```

---

## Summary

This Lambda Architecture provides:

✅ **Real-time processing** for immediate insights (< 5 seconds latency)
✅ **Batch processing** for historical data (daily aggregation)
✅ **Unified queries** combining both layers seamlessly
✅ **Scalability** through distributed components (Kafka, Spark, ClickHouse)
✅ **Fault tolerance** with message replay and checkpointing
✅ **Performance** via columnar storage and pre-aggregation
✅ **Flexibility** for both operational and analytical queries

**Total Data Flow**: Producer → Kafka → [Speed Layer + Batch Layer] → Serving Layer → Power BI
