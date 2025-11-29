# Retail Inventory - Lambda Architecture MVP

A complete **Lambda Architecture** implementation for real-time and batch processing of retail inventory data, featuring machine learning predictions and interactive dashboards.

## 🏗️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Data Generation                          │
│                  (Python Producer + Faker)                   │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │  Apache Kafka  │ (Message Queue)
                 │ retail_events  │
                 └────────┬───────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌────────────────┐ ┌──────────────┐ ┌─────────────┐
│  SPEED LAYER   │ │ BATCH LAYER  │ │ ORCHESTRATION│
│  ClickHouse    │ │ Apache Spark │ │   Airflow   │
│  (Real-time)   │ │   + MinIO    │ │   (Daily)   │
└────────┬───────┘ └──────┬───────┘ └─────────────┘
         │                │
         │                ▼
         │         ┌──────────────┐
         │         │    MinIO     │ (Data Lake)
         │         │   Parquet    │
         │         └──────┬───────┘
         │                │
         └────────┬───────┘
                  ▼
         ┌────────────────┐
         │ SERVING LAYER  │
         │   ClickHouse   │
         │  Unified View  │
         └────────┬───────┘
                  │
         ┌────────┴───────┬────────────┐
         │                │            │
         ▼                ▼            ▼
  ┌──────────┐   ┌──────────────┐  ┌──────────┐
  │Power BI  │   │  Streamlit   │  │ML Predict│
  │Dashboard │   │  Analytics   │  │ Pipeline │
  └──────────┘   └──────────────┘  └──────────┘
```

### Architecture Layers

1. **Speed Layer (Real-time)**
   - Producer generates events → Kafka → ClickHouse Kafka Engine → MergeTree table
   - Latency: < 5 seconds
   - Use case: Live dashboards, real-time monitoring

2. **Batch Layer (Historical)**
   - Kafka → Spark streaming → MinIO (Parquet) → ClickHouse S3 Engine
   - Schedule: Daily via Airflow
   - Use case: Historical analysis, data lake storage

3. **Serving Layer (Query Interface)**
   - Unified view combining real-time + historical data
   - Pre-aggregated materialized views for performance
   - Use case: BI tools, analytics dashboards

## 📊 Data Schema

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
- `event_time`: Transaction timestamp (YYYY-MM-DD HH:MM:SS)
- `store_id`: Store identifier (1-10)
- `product_id`: Product name (Laptop, T-Shirt, Coffee Maker, etc.)
- `category`: Product category (Electronics, Clothing, Home, Books, Sports)
- `transaction_type`: Transaction type (SALE, RETURN, RESTOCK)
- `quantity`: Number of items
- `unit_price`: Price per unit in dollars

## 🚀 Quick Start

### Prerequisites

- **Docker** & **Docker Compose**
- **Python 3.8+** (for Streamlit dashboards)
- **Power BI Desktop** (optional, for BI visualization)
- At least **8GB RAM** available

### 1. Clone and Navigate

```powershell
cd c:\Users\yassi\Desktop\BigDATA
```

### 2. Start All Services

```powershell
docker-compose up -d
```

This starts:
- **Zookeeper** (port 2181)
- **Kafka** (port 9092)
- **MinIO** (ports 9000, 9001)
- **ClickHouse** (ports 8123, 9010)
- **Spark** (Master: 7077, 8090)
- **Airflow** (port 8081)
- **PostgreSQL** (Airflow metadata)
- **Producer** (event generation)

### 3. Wait for Initialization (2-3 minutes)

Check service status:

```powershell
docker-compose ps
```

### 4. Verify Data Flow

**Check producer logs:**
```powershell
docker logs -f inventory-producer
```

**Check Kafka messages:**
```powershell
docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 5
```

**Query ClickHouse for real-time data:**
```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.retail_events_realtime"
```

**View sample events:**
```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT * FROM retail.retail_events_unified LIMIT 10" --format=Pretty
```

## 📈 Streamlit Dashboards

### Features

- **Home Dashboard**: System health, KPIs, architecture overview
- **Real-Time Sales**: Live monitoring with auto-refresh (30s)
- **Historical Analysis**: Trends, heatmaps, store comparisons
- **ML Predictions**: 7-day demand forecasting with model metrics
- **Anomaly Detection**: Z-score based sales anomaly alerts
- **Inventory Insights**: Stock movements, restock priorities

### Installation

```powershell
cd streamlit_app
pip install -r requirements.txt
```

### Run Dashboards

**Option 1: Using batch script (Windows)**
```powershell
.\run.bat
```

**Option 2: Using Streamlit CLI**
```powershell
streamlit run Home.py
```

**Access**: http://localhost:8501

### Configuration

Edit `streamlit_app/config.py` for ClickHouse connection:

```python
CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 8123
CLICKHOUSE_DATABASE = 'retail'
CLICKHOUSE_USER = 'default'
CLICKHOUSE_PASSWORD = 'password123'
```

See [Streamlit README](streamlit_app/README.md) for detailed documentation.

## 🤖 Machine Learning Pipeline

### Demand Forecasting

Automated 7-day ahead demand prediction using Random Forest Regressor.

**Features:**
- Daily predictions per product/store/category
- Feature engineering: hour, day, weekend flag, rolling averages
- Model metrics: RMSE, MAE, R²
- Automated ClickHouse import

### Run ML Pipeline

```powershell
cd spark
python ml_demand_forecast.py
```

### View Predictions

```sql
SELECT * FROM retail.demand_predictions 
WHERE prediction_date >= today() 
ORDER BY prediction_date, predicted_demand DESC 
LIMIT 10;
```

### Model Performance

```sql
SELECT * FROM retail.model_metrics 
ORDER BY training_timestamp DESC 
LIMIT 1;
```

See [ML Guide](docs/ML_GUIDE.md) for complete documentation.

## 🔌 Power BI Connection

### Method 1: ClickHouse ODBC Driver (Recommended)

1. **Download Driver**: [ClickHouse ODBC Releases](https://github.com/ClickHouse/clickhouse-odbc/releases)

2. **Configure ODBC DSN**:
   - Open Windows ODBC Data Source Administrator (64-bit)
   - Add System DSN → ClickHouse ODBC Driver
   - Configure connection:
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

1. Open Power BI Desktop
2. Get Data → Web
3. Use ClickHouse HTTP API:

```
http://localhost:8123/?user=default&password=password123&query=SELECT * FROM retail.retail_events_unified FORMAT JSON
```

### Recommended Tables for Dashboards

**Pre-Aggregated (Fastest):**
- `retail.daily_sales_summary` - Daily metrics
- `retail.hourly_sales_summary` - Hourly tracking
- `retail.product_performance_summary` - Product stats

**Analytics Views:**
- `retail.sales_anomaly_detection` - Unusual patterns
- `retail.return_rate_analysis` - Return rates
- `retail.store_performance_comparison` - Store comparison
- `retail.peak_hours_by_day` - Traffic patterns

**Raw Data:**
- `retail.retail_events_unified` - All events (real-time + historical)
- `retail.sales_by_category` - Category aggregation
- `retail.sales_by_store` - Store aggregation

**ML Predictions:**
- `retail.demand_predictions` - 7-day forecasts
- `retail.model_metrics` - Model performance
- `retail.prediction_accuracy` - Accuracy tracking

## 📂 Project Structure

```
BigDATA/
├── producer/                   # Event generation
│   ├── main.py                # Faker-based producer
│   └── Dockerfile
├── kafka/                     # Managed by docker-compose
├── clickhouse/
│   └── init.sql               # Database initialization
├── spark/
│   ├── batch_processor.py     # Batch processing job
│   ├── ml_demand_forecast.py  # ML pipeline
│   └── Dockerfile
├── airflow/
│   └── dags/
│       └── retail_dag.py      # Daily batch DAG
├── streamlit_app/             # Interactive dashboards
│   ├── Home.py                # Main dashboard
│   ├── pages/                 # Dashboard pages
│   ├── utils/                 # DB connector, charts
│   └── config.py              # Configuration
├── docs/
│   ├── DATAFLOW.md            # Architecture documentation
│   ├── SETUP.md               # Setup guide
│   ├── ML_GUIDE.md            # ML documentation
│   ├── REBUILD.md             # Data rebuild guide
│   └── BACKFILL_GUIDE.md      # Historical data backfill
├── docker-compose.yml         # Service orchestration
└── README.md                  # This file
```

## 🔧 Configuration Details

### Port Mappings

| Service            | Port(s)          | Access                          |
|--------------------|------------------|---------------------------------|
| Zookeeper          | 2181             | Internal only                   |
| Kafka              | 9092             | localhost:9092                  |
| MinIO API          | 9000             | http://localhost:9000           |
| MinIO Console      | 9001             | http://localhost:9001           |
| ClickHouse HTTP    | 8123             | http://localhost:8123           |
| ClickHouse Native  | 9010             | localhost:9010                  |
| Spark Master       | 7077, 8090       | http://localhost:8090           |
| Airflow Webserver  | 8081             | http://localhost:8081           |
| Streamlit App      | 8501             | http://localhost:8501           |

### Default Credentials

- **MinIO**: minioadmin / minioadmin
- **ClickHouse**: default / password123
- **Airflow**: admin / admin

## 🛠️ Common Operations

### View Producer Logs

```powershell
docker logs -f inventory-producer
```

### Query ClickHouse Interactively

```powershell
docker exec -it clickhouse clickhouse-client --user=default --password=password123
```

**Sample queries:**
```sql
-- Count real-time events
SELECT count() FROM retail.retail_events_realtime;

-- Sales by category
SELECT * FROM retail.sales_by_category;

-- Unified view
SELECT * FROM retail.retail_events_unified LIMIT 10;

-- ML predictions
SELECT * FROM retail.demand_predictions WHERE prediction_date >= today();
```

### Trigger Airflow DAG Manually

1. Open Airflow UI: http://localhost:8081
2. Login: admin / admin
3. Find "retail_batch_processing" DAG
4. Click play button to trigger

### Browse MinIO Data Lake

1. Open MinIO Console: http://localhost:9001
2. Login: minioadmin / minioadmin
3. Navigate to "retail-lake" bucket
4. View Parquet files organized by date

### Run ML Pipeline

```powershell
# From project root
cd spark
python ml_demand_forecast.py
```

### Rebuild Data (Clean Slate)

```powershell
# Use the rebuild script
.\rebuild.ps1
```

See [REBUILD.md](docs/REBUILD.md) for detailed instructions.

### Stop All Services

```powershell
# Stop services (keep data)
docker-compose down

# Stop and remove volumes (delete all data)
docker-compose down -v
```

## 🔍 Troubleshooting

### Kafka not starting

- **Issue**: Kafka fails to start
- **Solution**: 
  ```powershell
  docker-compose down -v
  docker-compose up -d kafka zookeeper
  ```

### ClickHouse connection refused

- **Issue**: Can't connect to ClickHouse
- **Solution**:
  ```powershell
  # Verify ClickHouse is running
  docker ps | findstr clickhouse
  
  # Test ping
  curl http://localhost:8123/ping
  
  # Check logs
  docker logs clickhouse
  ```

### No data in ClickHouse

- **Issue**: Real-time table is empty
- **Solution**:
  1. Check producer: `docker logs inventory-producer`
  2. Verify Kafka has data:
     ```powershell
     docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 5
     ```
  3. Restart ClickHouse: `docker restart clickhouse`

### Spark job fails

- **Issue**: Batch processor can't write to MinIO
- **Solution**:
  ```powershell
  # Check Spark logs
  docker logs spark-master
  
  # Verify MinIO is accessible
  docker exec spark-master curl http://minio:9000/minio/health/live
  ```

### Airflow DAG not appearing

- **Issue**: DAG doesn't show in UI
- **Solution**:
  ```powershell
  # Check DAG list
  docker exec airflow-webserver airflow dags list
  
  # View scheduler logs
  docker logs airflow-scheduler
  
  # Refresh DAGs in UI (trigger button)
  ```

### Streamlit connection error

- **Issue**: "Failed to connect to ClickHouse"
- **Solution**:
  1. Ensure ClickHouse is running: `docker ps | findstr clickhouse`
  2. Test connection: `curl http://localhost:8123/ping`
  3. Check credentials in `streamlit_app/config.py`

### ML predictions not showing

- **Issue**: No data in demand_predictions table
- **Solution**:
  1. Run ML pipeline: `cd spark && python ml_demand_forecast.py`
  2. Check table: `SELECT count() FROM retail.demand_predictions;`
  3. See [ML_GUIDE.md](docs/ML_GUIDE.md) for setup

## 📊 Sample Dashboard Ideas

### Real-Time Sales Dashboard

- **Total Revenue** (Card visualization)
- **Transactions Count** (KPI)
- **Sales by Category** (Pie/Donut chart)
- **Hourly Trend** (Line chart with auto-refresh)
- **Top 10 Products** (Bar chart)
- **Store Performance Map** (Geographic visualization)

### Historical Analysis Dashboard

- **Month-over-Month Growth** (Line chart)
- **Category Performance** (Matrix/Heatmap)
- **Seasonal Trends** (Area chart)
- **Return Rate Analysis** (Funnel chart)
- **Peak Hours Heatmap** (Day vs Hour)

### ML Predictions Dashboard

- **7-Day Demand Forecast** (Line chart with confidence bands)
- **Model Accuracy Metrics** (Gauge charts: RMSE, MAE, R²)
- **Prediction vs Actual** (Comparison chart)
- **Restock Recommendations** (Table with priority)
- **Product Demand Trends** (Multi-line chart)

### Executive Summary

- **Key Metrics**: Revenue, Transactions, Avg. Basket
- **YoY Growth**: Comparison charts
- **Store Rankings**: Leaderboard
- **Alert Panel**: Anomalies, low stock, high returns

## 🎯 Advanced Features

### Data Retention & TTL

ClickHouse automatically removes data older than 90 days:

```sql
-- Configured in init.sql
ALTER TABLE retail_events_realtime 
MODIFY TTL event_time + INTERVAL 90 DAY;
```

### Materialized Views

Pre-aggregated views for instant query responses:

- `daily_sales_summary` - SummingMergeTree (50-100x faster)
- `hourly_sales_summary` - Real-time aggregation
- `product_performance_summary` - Product analytics

### Anomaly Detection

Z-score based detection with configurable sensitivity:

```sql
SELECT * FROM retail.sales_anomaly_detection 
WHERE abs(z_score) > 2.0  -- 2 standard deviations
ORDER BY hour DESC;
```

### Scalability Considerations

Current capacity: **~173K events/day** (2 events/sec)

To scale up:
- **Producer**: Increase event rate or add multiple producers
- **Kafka**: Add more partitions and brokers
- **Spark**: Increase worker count and memory
- **ClickHouse**: Enable clustering and replication

## 📚 Documentation

- [DATAFLOW.md](docs/DATAFLOW.md) - Detailed architecture and data flow
- [SETUP.md](docs/SETUP.md) - Setup and installation guide
- [ML_GUIDE.md](docs/ML_GUIDE.md) - Machine learning pipeline
- [REBUILD.md](docs/REBUILD.md) - Data rebuild procedures
- [BACKFILL_GUIDE.md](docs/BACKFILL_GUIDE.md) - Historical backfilling
- [Streamlit README](streamlit_app/README.md) - Dashboard documentation

## 🤝 Support

For issues or questions:

1. Check **Troubleshooting** section above
2. Review relevant documentation in `docs/`
3. Check component logs: `docker logs <container-name>`
4. Review ClickHouse queries in `clickhouse/init.sql`

## 🎓 Learning Resources

**Lambda Architecture:**
- [Lambda Architecture Explained](http://lambda-architecture.net/)

**Technologies Used:**
- [Apache Kafka](https://kafka.apache.org/documentation/)
- [Apache Spark](https://spark.apache.org/docs/latest/)
- [ClickHouse](https://clickhouse.com/docs/en/intro)
- [MinIO](https://min.io/docs/minio/linux/index.html)
- [Apache Airflow](https://airflow.apache.org/docs/)
- [Streamlit](https://docs.streamlit.io/)

## 📝 License

This is an MVP project for educational and demonstration purposes.

## ✨ Features Summary

✅ **Real-time processing** with < 5s latency  
✅ **Batch processing** for historical data  
✅ **Lambda Architecture** combining speed & batch layers  
✅ **ML demand forecasting** with automated predictions  
✅ **Interactive Streamlit dashboards** for analytics  
✅ **Power BI integration** via ODBC and HTTP  
✅ **Anomaly detection** for unusual sales patterns  
✅ **Pre-aggregated views** for instant queries  
✅ **Data lake storage** with Parquet compression  
✅ **Airflow orchestration** for scheduling  
✅ **Auto-cleanup** with 90-day TTL  
✅ **Docker-based** for easy deployment  

---

**Built with:** Kafka • Spark • ClickHouse • MinIO • Airflow • Streamlit • Python
