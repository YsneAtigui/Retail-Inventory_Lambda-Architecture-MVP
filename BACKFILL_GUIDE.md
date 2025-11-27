# Historical Data Backfill - Quick Reference

## How to Run

### Option 1: Using Docker (Recommended)
```powershell
# Run backfill inside the producer container
docker exec -it inventory-producer python /app/backfill_historical.py
```

### Option 2: Standalone
```powershell
# Install dependencies first
pip install kafka-python faker

# Run locally
cd producer
python backfill_historical.py
```

## Configuration

Edit `backfill_historical.py` to adjust:

```python
MONTHS_TO_BACKFILL = 12  # How many months of data (default: 12 = 1 year)
EVENTS_PER_HOUR = 5      # Events per hour (default: 5)
```

## What It Does

Generates realistic historical data with:

- ✅ **Seasonal patterns**: Higher sales in Nov-Dec (holidays), lower in Jan-Feb
- ✅ **Hourly patterns**: Peak sales during 9 AM-12 PM and 5 PM-8 PM
- ✅ **Weekend boost**: 40% more sales on Saturdays and Sundays
- ✅ **Price variations**: Slight inflation over time, seasonal discounts
- ✅ **Transaction mix**: 90% SALE, 7% RETURN, 3% RESTOCK

## Expected Results

**For 12 months:**
- Total events: ~43,200 events (12 months × 30 days × 24 hours × 5 events/hour)
- Runtime: ~5-10 minutes
- Data distributed realistically across all months

**For 24 months (2 years):**
- Total events: ~86,400 events
- Runtime: ~10-15 minutes

## After Backfill

### Verify Data in ClickHouse

```powershell
# Check total events
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT count(), min(event_time), max(event_time) FROM retail.retail_events_realtime"

# Check monthly distribution
docker exec clickhouse clickhouse-client --user=default --password=password123 --query="SELECT toYYYYMM(event_time) as month, count() as events FROM retail.retail_events_realtime GROUP BY month ORDER BY month" --format=Pretty
```

### View in Power BI

Your existing dashboards will now show:
- Year-over-year comparisons
- Seasonal trends
- Monthly/quarterly reports
- Historical forecasting data

## Customization

### Add More Variety
To make data even more realistic, you can adjust in the script:

**Seasonal factors** (line 35):
```python
seasonal_factors = {
    1: 0.7,   # Post-holiday slump
    11: 1.5,  # Black Friday
    12: 1.8   # Christmas
}
```

**Hourly patterns** (line 49):
```python
if 17 <= hour <= 20:
    return 1.7  # Evening peak hours
```

**Store-specific patterns**:
```python
# Busy stores vs quiet stores
store_multipliers = {
    1: 1.5,   # Flagship store
    10: 0.7   # Small branch
}
```

## Tips

- **Start small**: Try 3-6 months first to test
- **Monitor Kafka**: Watch `docker logs kafka` for any issues  
- **ClickHouse lag**: Data appears in ClickHouse within 30-60 seconds
- **Stop anytime**: Press Ctrl+C to interrupt (data already sent is kept)

## Troubleshooting

**"Connection refused":**
```powershell
# Make sure Kafka is running
docker ps | grep kafka
```

**"Too slow":**
```python
# Increase batch size in script
EVENTS_PER_HOUR = 10  # Generate more events
```

**"Want specific dates":**
```python
# Modify in script
start_date = datetime(2023, 1, 1)  # Custom start
end_date = datetime(2024, 12, 31)  # Custom end
```
