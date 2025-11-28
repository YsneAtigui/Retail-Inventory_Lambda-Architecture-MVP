# Complete Project Rebuild Guide

This guide explains how to completely remove all existing data and rebuild the project from scratch with fresh data.

## 🎯 What This Does

The rebuild process will:
1. **Stop all running services** (Kafka, ClickHouse, MinIO, Spark, Airflow, Producer)
2. **Delete all data volumes** (ClickHouse tables, MinIO files, Kafka topics)
3. **Remove all containers**
4. **Start fresh services**
5. **Reinitialize database schema**
6. **Begin generating new data**

> [!WARNING]
> **This will permanently delete ALL existing data!** Make sure you have backups if needed.

## 🚀 Quick Rebuild (Automated)

### Option 1: PowerShell Script (Recommended for Windows)

```powershell
cd C:\Users\yassi\Desktop\BigDATA
.\rebuild.ps1
```

The script will:
- Ask for confirmation before proceeding
- Automatically execute all rebuild steps
- Verify service health
- Check data flow
- Display status for each component

**Expected Duration:** ~3-5 minutes

---

## 🛠️ Manual Rebuild (Step-by-Step)

If you prefer to run commands manually or need to troubleshoot:

### Step 1: Stop All Services

```powershell
cd C:\Users\yassi\Desktop\BigDATA
docker-compose down
```

### Step 2: Remove All Data

```powershell
# Remove all volumes (this deletes all data)
docker-compose down -v

# Optional: Clean up orphaned containers
docker container prune -f
```

### Step 3: Start Services

```powershell
docker-compose up -d
```

### Step 4: Wait for Initialization

```powershell
# Wait 90 seconds for all services to start
Start-Sleep -Seconds 90
```

### Step 5: Initialize ClickHouse Database

```powershell
Get-Content clickhouse/init.sql | docker exec -i clickhouse clickhouse-client --user=default --password=password123 --multiquery
```

This creates:
- Database schema
- Tables (real-time, historical, unified views)
- Materialized views
- Kafka engine for real-time ingestion

### Step 6: Verify Services

Check each service is running:

```powershell
# Check all containers
docker ps

# Check Kafka
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Check ClickHouse
Invoke-WebRequest -Uri "http://localhost:8123/ping"

# Check MinIO
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live"
```

### Step 7: Verify Data Flow

Wait 2-3 minutes, then check:

**Kafka Messages:**
```powershell
docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 5
```

**ClickHouse Data:**
```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.retail_events_realtime"
```

**Sample Events:**
```powershell
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT * FROM retail.retail_events_unified LIMIT 10" --format=Pretty
```

---

## 🔍 Verification Checklist

After rebuild, verify:

- [ ] All 8 containers are running (`docker ps`)
- [ ] Producer is generating events (`docker logs inventory-producer`)
- [ ] Kafka has messages in `retail_events` topic
- [ ] ClickHouse has data in `retail.retail_events_realtime`
- [ ] MinIO console accessible at http://localhost:9001
- [ ] Airflow UI accessible at http://localhost:8081
- [ ] Spark UI accessible at http://localhost:8090

---

## 📊 What Gets Created

### ClickHouse Tables

**Real-time Layer:**
- `retail.retail_events_realtime` - MergeTree table for speed layer
- `retail.retail_events_queue` - Kafka engine (consumes from Kafka)
- `retail.retail_events_mv` - Materialized view (queue → realtime)

**Batch Layer:**
- `retail.retail_events_historical` - S3 engine (reads from MinIO)

**Serving Layer:**
- `retail.retail_events_unified` - Union of real-time + historical
- `retail.sales_by_category` - Aggregated view
- `retail.sales_by_store` - Store performance
- `retail.hourly_sales_trend` - Time-series data
- `retail.product_performance` - Product analytics

### Kafka Topics

- `retail_events` - Main topic for all events

### MinIO Buckets

- `retail-lake` - Parquet files from Spark batch processing

---

## ⏱️ Timeline: When to Expect Data

| Time | What's Happening |
|------|------------------|
| 0 min | Services starting |
| 1-2 min | Kafka & ClickHouse ready |
| 2-3 min | Producer starts sending events to Kafka |
| 3-5 min | Real-time data appears in ClickHouse |
| 24 hrs | First Airflow batch job runs (midnight) |
| 24+ hrs | Historical data in MinIO (Spark → Parquet) |

> [!TIP]
> **For immediate testing**: Real-time data will be available in 3-5 minutes. You don't need to wait for batch processing.

---

## 🚑 Troubleshooting

### No Data in ClickHouse After 5 Minutes

**Check Producer:**
```powershell
docker logs inventory-producer
```
Expected output: "Published message to retail_events"

**Check Kafka:**
```powershell
docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 1
```
Should show JSON event data

**Restart ClickHouse:**
```powershell
docker restart clickhouse
Start-Sleep -Seconds 20
Get-Content clickhouse/init.sql | docker exec -i clickhouse clickhouse-client --user=default --password=password123 --multiquery
```

### Services Won't Start

**Check Docker resources:**
- Ensure Docker Desktop has at least 8GB RAM allocated
- Free up disk space if needed

**View specific service logs:**
```powershell
docker logs kafka
docker logs clickhouse
docker logs inventory-producer
```

### Kafka Consumer Group Errors

```powershell
# Reset Kafka (removes all topics and data)
docker-compose restart kafka
```

### ClickHouse Connection Refused

```powershell
# Wait longer for ClickHouse to initialize
Start-Sleep -Seconds 30

# Test connection
Invoke-WebRequest -Uri "http://localhost:8123/ping"
```

---

## 🔄 Partial Rebuilds

### Reset Only ClickHouse Data

```powershell
# Truncate tables without stopping services
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="TRUNCATE TABLE retail.retail_events_realtime"
```

### Reset Only MinIO Data

```powershell
# Delete bucket contents via MinIO console
# http://localhost:9001 → retail-lake → Delete all objects
```

### Reset Only Kafka Topics

```powershell
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic retail_events
docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic retail_events --partitions 3 --replication-factor 1
```

---

## 📝 Notes

- **Data Generation Rate**: Producer sends ~1 event per second by default
- **Storage Requirements**: ~100MB per day (varies with event rate)
- **Batch Processing**: Runs daily at midnight (see Airflow DAG)
- **Data Retention**: 90 days (configured in ClickHouse TTL)

---

## 🎯 Next Steps After Rebuild

1. **Wait 5-10 minutes** for data to accumulate
2. **Connect Streamlit Dashboard**: http://localhost:8501 (if running)
3. **Connect Power BI** using ODBC or HTTP connector
4. **Monitor Airflow**: http://localhost:8081 (admin/admin)
5. **View Spark Jobs**: http://localhost:8090

For detailed usage, see [README.md](README.md) and [SETUP.md](SETUP.md).
