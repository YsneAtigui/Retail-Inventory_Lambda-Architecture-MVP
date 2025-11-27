#!/bin/bash

# Lambda Architecture MVP - Startup Script
# This script starts all services and initializes the system

echo "========================================="
echo "Lambda Architecture MVP - Startup"
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Start all services
echo "📦 Starting all services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to initialize (60 seconds)..."
sleep 60

echo ""
echo "🔍 Checking service health..."
echo ""

# Check Kafka
echo -n "  Kafka: "
if docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "⚠ Not ready"
fi

# Check MinIO
echo -n "  MinIO: "
if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "⚠ Not accessible"
fi

# Check ClickHouse
echo -n "  ClickHouse: "
if curl -s http://localhost:8123/ping > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "⚠ Not accessible"
fi

# Check Spark
echo -n "  Spark Master: "
if curl -s http://localhost:8090 > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "⚠ Not accessible"
fi

# Check Airflow
echo -n "  Airflow: "
if curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "✓ Running"
else
    echo "⚠ Not ready"
fi

echo ""
echo "📝 Initializing ClickHouse tables..."

# Wait a bit more for ClickHouse to be fully ready
sleep 10

# Initialize ClickHouse
docker cp clickhouse/init.sql clickhouse:/tmp/init.sql 2>/dev/null
docker exec clickhouse clickhouse-client --user=default --password=password123 --queries-file=/tmp/init.sql 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✓ ClickHouse tables initialized"
else
    echo "⚠ ClickHouse initialization had issues (may already be initialized)"
fi

echo ""
echo "========================================="
echo "✅ Lambda Architecture MVP is running!"
echo "========================================="
echo ""
echo "📊 Access Points:"
echo "  • MinIO Console:    http://localhost:9001 (minioadmin/minioadmin)"
echo "  • ClickHouse HTTP:  http://localhost:8123"
echo "  • Spark Master UI:  http://localhost:8090"
echo "  • Airflow UI:       http://localhost:8081 (admin/admin)"
echo ""
echo "🔌 Power BI Connection:"
echo "  • Host:     localhost"
echo "  • Port:     8123"
echo "  • Database: retail"
echo "  • User:     default"
echo "  • Password: password123"
echo ""
echo "📖 For more details, see README.md"
echo ""
