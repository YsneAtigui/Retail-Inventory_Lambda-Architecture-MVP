# Retail Inventory - Lambda Architecture MVP

A complete Lambda Architecture implementation for real-time and batch processing of retail inventory data, with Power BI visualization support.

## 🏗️ Architecture Overview

```
┌─────────────┐
│   Producer  │ (Faker + Kafka)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Kafka    │ (KRaft Mode)
└──────┬──────┘
       │
       ├──────────────────┬─────────────────┐
       │                  │                 │
       ▼                  ▼                 ▼
┌─────────────┐    ┌──────────┐    ┌──────────┐
│ ClickHouse  │    │  Spark   │    │ Airflow  │
│ (Real-time) │    │ (Batch)  │    │ (Orch.)  │
└─────────────┘    └────┬─────┘    └──────────┘
                        │
                        ▼
                  ┌──────────┐
                  │  MinIO   │ (Data Lake)
                  └────┬─────┘
                       │
                       ▼
                 ┌──────────┐
                 │ClickHouse│ (Historical)
                 └────┬─────┘
                      │
                      ▼
               ┌──────────────┐
               │  Unified     │
               │  View        │
               └──────┬───────┘
                      │
                      ▼
                 ┌─────────┐
                 │Power BI │
                 └─────────┘
```

## 📊 Data Schema

All events follow this JSON schema:

```json
{
  "event_time": "2023-10-27 10:00:00",
  "store_id": 1,
  "product_id": "Laptop",
  "category": "Electronics",
  "transaction_type": "SALE",
  "quantity": 5,
  "unit_price": 450.00
}
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Power BI Desktop (for visualization)
- At least 8GB RAM available

### 1. Start the Stack

```bash
# Navigate to project directory
cd c:\Users\yassi\Desktop\BigDATA

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 2. Verify Services

Wait 2-3 minutes for all services to initialize, then verify:

- **Kafka**: `docker exec -it kafka kafka-topics.sh --bootstrap-server localhost:9092 --list`
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **ClickHouse**: http://localhost:8123/ping (should return "Ok.")
- **Spark Master UI**: http://localhost:8090
- **Airflow UI**: http://localhost:8081 (admin/admin)

### 3. Initialize ClickHouse Tables

```bash
# Execute the initialization script
docker exec -it clickhouse clickhouse-client --user=default --password=password123 --multiquery < clickhouse/init.sql

# Or copy and execute manually
docker cp clickhouse/init.sql clickhouse:/tmp/init.sql
docker exec -it clickhouse clickhouse-client --user=default --password=password123 --queries-file=/tmp/init.sql
```

### 4. Verify Data Flow

```bash
# Check producer logs
docker logs -f inventory-producer

# Query ClickHouse for real-time data
docker exec -it clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.retail_events_realtime"

# Check MinIO for Parquet files
# Open http://localhost:9001 and browse to retail-lake bucket
```

## 🔌 Power BI Connection

### Method 1: ClickHouse ODBC Driver (Recommended)

1. **Download Driver**: Install ClickHouse ODBC driver from https://github.com/ClickHouse/clickhouse-odbc/releases

2. **Configure ODBC**:
   - Open Windows ODBC Data Source Administrator (64-bit)
   - Add new System DSN
   - Select ClickHouse ODBC Driver
   - Configure:
     - **Name**: ClickHouse-Retail
     - **Host**: localhost
     - **Port**: 8123
     - **Database**: retail
     - **User**: default
     - **Password**: password123

3. **Connect in Power BI**:
   - Open Power BI Desktop
   - Get Data → ODBC
   - Select "ClickHouse-Retail" DSN
   - Choose tables/views to import

### Method 2: Web Connector (Alternative)

1. **Open Power BI Desktop**

2. **Get Data → Web**

3. **Use ClickHouse HTTP API**:
   ```
   http://localhost:8123/?user=default&password=password123&query=SELECT * FROM retail.retail_events_unified FORMAT JSON
   ```

4. **Parse JSON response** in Power Query

### Recommended Tables/Views for Power BI

- **`retail_events_unified`**: Combined real-time and historical data
- **`sales_by_category`**: Aggregated sales by product category
- **`sales_by_store`**: Aggregated sales by store
- **`hourly_sales_trend`**: Time-series sales data
- **`product_performance`**: Top-performing products

## 📁 Project Structure

```
BigDATA/
├── docker-compose.yml          # All service definitions
├── producer/
│   ├── main.py                 # Kafka producer with Faker
│   ├── Dockerfile
│   └── requirements.txt
├── spark/
│   └── batch_processor.py      # PySpark batch job
├── airflow/
│   └── dags/
│       └── retail_dag.py       # Daily batch processing DAG
├── clickhouse/
│   └── init.sql                # Database initialization
└── README.md
```

## 🔧 Configuration Details

### Port Mappings

| Service            | Port(s)          | Access                          |
|--------------------|------------------|---------------------------------|
| Kafka              | 9092             | kafka:9092 (internal)           |
| MinIO API          | 9000             | http://localhost:9000           |
| MinIO Console      | 9001             | http://localhost:9001           |
| ClickHouse HTTP    | 8123             | http://localhost:8123           |
| ClickHouse Native  | 9010             | localhost:9010                  |
| Spark Master       | 7077, 8090       | spark://localhost:7077          |
| Airflow            | 8081             | http://localhost:8081           |

### Default Credentials

- **MinIO**: minioadmin / minioadmin
- **ClickHouse**: default / password123
- **Airflow**: admin / admin

## 🛠️ Common Operations

### View Producer Logs

```bash
docker logs -f inventory-producer
```

### Query ClickHouse

```bash
# Interactive client
docker exec -it clickhouse clickhouse-client --user=default --password=password123

# Sample queries
SELECT count() FROM retail.retail_events_realtime;
SELECT * FROM retail.sales_by_category;
SELECT * FROM retail.retail_events_unified LIMIT 10;
```

### Trigger Airflow DAG Manually

1. Open Airflow UI: http://localhost:8081
2. Login (admin/admin)
3. Find "retail_batch_processing" DAG
4. Click play button to trigger

### Browse MinIO Data Lake

1. Open MinIO Console: http://localhost:9001
2. Login (minioadmin/minioadmin)
3. Navigate to "retail-lake" bucket
4. View Parquet files

### Stop All Services

```bash
docker-compose down

# To remove volumes (data will be lost)
docker-compose down -v
```

## 🔍 Troubleshooting

### Kafka not starting

- **Issue**: Kafka fails to start in KRaft mode
- **Solution**: Ensure `KAFKA_KRAFT_CLUSTER_ID` is set and volumes are clean
  ```bash
  docker-compose down -v
  docker-compose up -d kafka
  ```

### ClickHouse connection refused

- **Issue**: Can't connect to ClickHouse from Power BI
- **Solution**: 
  - Verify ClickHouse is running: `docker ps | grep clickhouse`
  - Test ping: `curl http://localhost:8123/ping`
  - Check firewall rules for port 8123

### No data in ClickHouse

- **Issue**: Real-time table is empty
- **Solution**:
  - Check producer is running: `docker logs inventory-producer`
  - Verify Kafka topic has data: 
    ```bash
    docker exec -it kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 5
    ```
  - Check materialized view: `SELECT count() FROM retail.retail_events_mv`

### Spark job fails

- **Issue**: Batch processor can't write to MinIO
- **Solution**: Verify S3A configuration and MinIO accessibility
  ```bash
  docker logs spark-master
  docker exec -it spark-master curl http://minio:9000/minio/health/live
  ```

### Airflow DAG not appearing

- **Issue**: DAG doesn't show in Airflow UI
- **Solution**:
  - Check DAG file syntax: `docker exec -it airflow-webserver airflow dags list`
  - View scheduler logs: `docker logs airflow-scheduler`
  - Refresh DAGs in UI

## 📈 Sample Power BI Dashboards

### Real-Time Sales Dashboard

- **Total Revenue** (Card visualization)
- **Sales by Category** (Pie chart)
- **Hourly Trend** (Line chart)
- **Top Products** (Bar chart)
- **Store Performance** (Map/Table)

### Historical Analysis

- **Month-over-Month Growth** (Line chart)
- **Category Performance** (Matrix)
- **Seasonal Trends** (Area chart)
- **Return Analysis** (Funnel chart)

## 🎯 Next Steps

1. **Optimize Performance**:
   - Tune Kafka partitions
   - Adjust Spark batch intervals
   - Add ClickHouse indexes

2. **Add Monitoring**:
   - Prometheus + Grafana
   - Alert on data delays
   - Track producer throughput

3. **Enhance Security**:
   - Replace hardcoded credentials
   - Enable TLS/SSL
   - Implement role-based access

4. **Scale Up**:
   - Add more Kafka brokers
   - Increase Spark workers
   - Implement data retention policies

## 📝 License

This is an MVP project for demonstration purposes.

## 🤝 Support

For issues or questions, check the troubleshooting section or review component logs.
