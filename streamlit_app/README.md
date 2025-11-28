# Streamlit Dashboards for Retail Analytics

Interactive data visualization dashboards for the Retail Inventory Lambda Architecture project, built with Streamlit and ClickHouse.

## 📊 Available Dashboards

### 1. Home (Overview)
- System status and health indicators
- Key performance metrics
- Data freshness monitoring
- Architecture overview

### 2. Real-Time Sales 📊
- Live sales monitoring with auto-refresh
- Hourly revenue and transaction trends
- Sales breakdown by category and store
- Top performing products
- KPI metrics (revenue, transactions, basket value)

### 3. Historical Analysis 📈
- Daily sales trends (7-90 days)
- Peak hours heatmap (day vs hour)
- Store performance comparison
- Return rate analysis
- Category performance breakdown

### 4. ML Predictions 🤖
- Demand forecasting (7-day ahead)
- Model performance metrics (RMSE, MAE, R²)
- Prediction vs actual analysis
- Restock recommendations
- Product/store drill-down

### 5. Anomaly Detection 🎯
- Automated anomaly detection using z-scores
- Sales confidence bands visualization
- Category-wise anomaly analysis
- Configurable sensitivity settings
- Alert summaries

### 6. Inventory Insights 📦
- Stock movement overview (sales/returns/restocks)
- High demand products identification
- Slow moving products analysis
- Restock priority matrix
- Category stock status

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- ClickHouse database running (via Docker)
- All services from docker-compose.yml started

### Install Dependencies

```bash
cd c:\Users\yassi\Desktop\BigDATA\streamlit_app
pip install -r requirements.txt
```

## ▶️ Running the Application

### Option 1: Using the batch script (Windows)
```bash
run.bat
```

### Option 2: Using Streamlit directly
```bash
streamlit run Home.py
```

### Option 3: Custom port
```bash
streamlit run Home.py --server.port 8501
```

The application will open automatically in your browser at `http://localhost:8501`

## 🔧 Configuration

### ClickHouse Connection
Edit `config.py` to modify connection settings:

```python
CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 8123
CLICKHOUSE_DATABASE = 'retail'
CLICKHOUSE_USER = 'default'
CLICKHOUSE_PASSWORD = 'password123'
```

### Theme & Styling
Customize the dashboard theme in `.streamlit/config.toml`:
- Primary colors
- Background colors
- Font preferences

## 📱 Dashboard Features

### Interactive Filters
- Time range selectors
- Product/store filters
- Category filters
- Date range pickers

### Auto-Refresh
The Real-Time Sales dashboard supports auto-refresh (30 seconds) for live monitoring.

### Data Caching
Queries are cached for 60 seconds to improve performance. Use the "Refresh Data" button to clear cache.

### Export Options
All data tables can be:
- Searched
- Sorted
- Exported (use Streamlit's built-in download features)

## 🗃️ Data Sources

The dashboards query the following ClickHouse tables/views:

**Core Tables:**
- `retail_events_realtime` - Real-time stream data
- `retail_events_historical` - Batch historical data
- `retail_events_unified` - Combined view

**Aggregation Views:**
- `sales_by_category`
- `sales_by_store`
- `hourly_sales_trend`
- `product_performance`
- `daily_sales_summary`
- `peak_hours_by_day`
- `store_performance_comparison`
- `return_rate_analysis`

**ML Tables:**
- `demand_predictions`
- `model_metrics`
- `prediction_accuracy`
- `daily_demand_forecast`

## 🛠️ Troubleshooting

### "Failed to connect to ClickHouse"
1. Ensure ClickHouse container is running:
   ```bash
   docker ps | grep clickhouse
   ```
2. Test connection:
   ```bash
   curl http://localhost:8123/ping
   ```
3. Check credentials in `config.py`

### "No data available"
1. Verify producer is running:
   ```bash
   docker logs -f inventory-producer
   ```
2. Check ClickHouse has data:
   ```bash
   docker exec -it clickhouse clickhouse-client --user=default --password=password123
   SELECT count() FROM retail.retail_events_realtime;
   ```

### ML Predictions showing "No data"
1. Ensure ML pipeline has run (see ML_GUIDE.md)
2. Check demand_predictions table:
   ```bash
   SELECT count() FROM retail.demand_predictions;
   ```

### Slow dashboard loading
1. Reduce date range in filters
2. Clear cache and refresh
3. Optimize ClickHouse queries (add indexes if needed)

## 📊 Architecture

```
Streamlit App
    ↓
utils/db_connector.py (ClickHouse client)
    ↓
ClickHouse Database (localhost:8123)
    ↓
Real-time + Batch Data (Lambda Architecture)
```

## 🎨 Customization

### Adding New Charts
Use the chart utilities in `utils/charts.py`:
```python
from utils.charts import create_line_chart, create_bar_chart

fig = create_line_chart(df, x='date', y='revenue', title='My Chart')
st.plotly_chart(fig)
```

### Adding New Dashboards
1. Create new file in `pages/` directory
2. Follow naming convention: `<number>_<emoji>_<Name>.py`
3. Use existing dashboards as templates

## 📝 Requirements

See `requirements.txt` for full dependency list:
- streamlit
- clickhouse-connect
- pandas
- plotly
- numpy

## 🤝 Support

For issues related to:
- **Dashboard functionality**: Check this README
- **Data issues**: See main project README.md
- **ClickHouse queries**: Review SQL files in clickhouse/ directory

## 📄 License

Part of the Retail Inventory Lambda Architecture MVP project.

---

**Powered by:** Streamlit + ClickHouse + Plotly
