# Lambda Architecture MVP - Complete Rebuild Script
# This script removes all data and rebuilds the project from scratch

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Lambda Architecture MVP - COMPLETE REBUILD" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  WARNING: This will DELETE ALL existing data!" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Are you sure you want to proceed? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "❌ Rebuild cancelled." -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🛑 Step 1: Stopping all services..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "🗑️  Step 2: Removing all volumes and data..." -ForegroundColor Yellow
docker-compose down -v

Write-Host ""
Write-Host "🧹 Step 3: Cleaning up Docker resources..." -ForegroundColor Yellow
# Remove any orphaned containers
docker container prune -f

Write-Host ""
Write-Host "📦 Step 4: Starting services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "⏳ Step 5: Waiting for services to initialize (90 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 90

Write-Host ""
Write-Host "🔍 Step 6: Checking service health..." -ForegroundColor Yellow

# Check Kafka
Write-Host "  Checking Kafka..." -NoNewline
try {
    docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list 2>&1 | Out-Null
    Write-Host " ✓" -ForegroundColor Green
} catch {
    Write-Host " ⚠ Not ready" -ForegroundColor Yellow
}

# Check MinIO
Write-Host "  Checking MinIO..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host " ✓" -ForegroundColor Green
} catch {
    Write-Host " ⚠ Not accessible" -ForegroundColor Yellow
}

# Check ClickHouse
Write-Host "  Checking ClickHouse..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8123/ping" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host " ✓" -ForegroundColor Green
} catch {
    Write-Host " ⚠ Not accessible" -ForegroundColor Yellow
}

# Check Spark
Write-Host "  Checking Spark Master..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8090" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host " ✓" -ForegroundColor Green
} catch {
    Write-Host " ⚠ Not accessible" -ForegroundColor Yellow
}

# Check Airflow
Write-Host "  Checking Airflow..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host " ✓" -ForegroundColor Green
} catch {
    Write-Host " ⚠ Not ready" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "⏳ Step 7: Waiting additional time for ClickHouse to be fully ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "📝 Step 8: Initializing ClickHouse database..." -ForegroundColor Yellow

# Initialize ClickHouse tables
try {
    Get-Content clickhouse/init.sql | docker exec -i clickhouse clickhouse-client --user=default --password=password123 --multiquery
    Write-Host "  ✓ ClickHouse tables created" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ ClickHouse initialization failed - check logs" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "⏳ Step 9: Waiting for producer to generate data (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "🔍 Step 10: Verifying data flow..." -ForegroundColor Yellow

# Check Kafka messages
Write-Host "  Checking Kafka messages..." -NoNewline
try {
    $kafkaOutput = docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic retail_events --from-beginning --max-messages 1 --timeout-ms 5000 2>&1
    if ($kafkaOutput) {
        Write-Host " ✓ Data flowing" -ForegroundColor Green
    } else {
        Write-Host " ⚠ No messages yet" -ForegroundColor Yellow
    }
} catch {
    Write-Host " ⚠ Unable to check" -ForegroundColor Yellow
}

# Check ClickHouse data
Write-Host "  Checking ClickHouse data..." -NoNewline
try {
    $count = docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count() FROM retail.retail_events_realtime" 2>&1
    if ($count -match '^\d+$' -and [int]$count -gt 0) {
        Write-Host " ✓ $count records" -ForegroundColor Green
    } else {
        Write-Host " ⚠ No data yet (wait a few more minutes)" -ForegroundColor Yellow
    }
} catch {
    Write-Host " ⚠ Unable to check" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✅ Rebuild Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Access Points:" -ForegroundColor White
Write-Host "  • MinIO Console:    http://localhost:9001 (minioadmin/minioadmin)" -ForegroundColor Gray
Write-Host "  • ClickHouse HTTP:  http://localhost:8123" -ForegroundColor Gray
Write-Host "  • Spark Master UI:  http://localhost:8090" -ForegroundColor Gray
Write-Host "  • Airflow UI:       http://localhost:8081 (admin/admin)" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Next Steps:" -ForegroundColor White
Write-Host "  1. Wait 5-10 minutes for data to accumulate" -ForegroundColor Gray
Write-Host "  2. Check real-time dashboard: http://localhost:8081" -ForegroundColor Gray
Write-Host "  3. Verify data in ClickHouse:" -ForegroundColor Gray
Write-Host "     docker exec clickhouse clickhouse-client --user=default --password=password123 --query=\""SELECT count() FROM retail.retail_events_unified\""" -ForegroundColor DarkGray
Write-Host ""
Write-Host "📖 For more details, see README.md" -ForegroundColor Gray
Write-Host ""
