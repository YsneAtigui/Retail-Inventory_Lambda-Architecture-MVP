# Lambda Architecture MVP - Setup Guide

## Quick Start

### 1. Start All Services
```powershell
cd C:\Users\yassi\Desktop\BigDATA
docker-compose up -d
```

### 2. Wait for Services (2-3 minutes)
All containers need time to initialize. Check status:
```powershell
docker ps
```

### 3. Initialize ClickHouse Database
```powershell
Get-Content clickhouse/init.sql | docker exec -i clickhouse clickhouse-client --user=default --password=password123 --multiquery
```

### 4. Verify Data Flow

**Check Kafka messages:**
```powershell
docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 5
```

**Check ClickHouse data (wait 2-3 minutes after init):**
```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.retail_events_realtime"
```

**View sample events:**
```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT * FROM retail.retail_events_unified LIMIT 10" --format=Pretty
```

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| Spark Master UI | http://localhost:8090 | - |
| Airflow UI | http://localhost:8081 | admin / admin |
| ClickHouse HTTP | http://localhost:8123/ping | default / password123 |

## Power BI Connection

### Method 1: ODBC (Recommended)
1. Install ClickHouse ODBC driver: https://github.com/ClickHouse/clickhouse-odbc/releases
2. Create System DSN:
   - **Host**: localhost
   - **Port**: 8123
   - **Database**: retail
   - **User**: default
   - **Password**: password123
3. In Power BI: Get Data → ODBC → Select DSN

### Method 2: HTTP/Web
1. In Power BI: Get Data → Web
2. URL: `http://localhost:8123/?user=default&password=password123&query=SELECT * FROM retail.retail_events_unified FORMAT JSON`

## Useful Tables for Dashboards

- `retail.retail_events_unified` - All events (real-time + historical)
- `retail.sales_by_category` - Aggregated by category
- `retail.sales_by_store` - Aggregated by store  
- `retail.hourly_sales_trend` - Time-series hourly data
- `retail.product_performance` - Top products

## Stop/Restart Services

```powershell
# Stop all
docker-compose down

# Restart all
docker-compose up -d

# View logs
docker logs -f <container-name>
```

## Troubleshooting

**No data in ClickHouse?**
- Wait 3-5 minutes after initialization
- Check Kafka has data: `docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list`
- Restart ClickHouse: `docker restart clickhouse`

**Producer errors?**
- Check logs: `docker logs inventory-producer`
- Restart: `docker restart inventory-producer`

**Airflow DAG missing?**
- Check scheduler: `docker logs airflow-scheduler`
- List DAGs: `docker exec airflow-webserver airflow dags list`

## Architecture Components

```
Producer (Faker) → Kafka → ClickHouse (Real-time)
                     ↓
                  Spark → MinIO (Parquet) → ClickHouse (Historical)
                     ↓
                 Airflow (Orchestration)
```

**Speed Layer**: Producer → Kafka → ClickHouse MergeTree
**Batch Layer**: Kafka → Spark → MinIO → ClickHouse S3 Engine  
**Serving Layer**: ClickHouse Unified View → Power BI
