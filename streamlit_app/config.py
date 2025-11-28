# Configuration for Streamlit Dashboards

# ClickHouse Connection Settings
CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 8123
CLICKHOUSE_DATABASE = 'retail'
CLICKHOUSE_USER = 'default'
CLICKHOUSE_PASSWORD = 'password123'

# Dashboard Theme Colors
PRIMARY_COLOR = '#1f77b4'
SECONDARY_COLOR = '#ff7f0e'
SUCCESS_COLOR = '#2ecc71'
WARNING_COLOR = '#f39c12'
DANGER_COLOR = '#e74c3c'
INFO_COLOR = '#3498db'

# Chart Color Palette (vibrant, modern colors)
CHART_COLORS = [
    '#667eea',  # Purple
    '#764ba2',  # Deep Purple
    '#f093fb',  # Pink
    '#4facfe',  # Blue
    '#00f2fe',  # Cyan
    '#43e97b',  # Green
    '#38f9d7',  # Teal
    '#fa709a',  # Rose
    '#fee140',  # Yellow
    '#ffa726',  # Orange
]

# Plotly Chart Template
PLOTLY_TEMPLATE = 'plotly_dark'

# Dashboard Settings
AUTO_REFRESH_INTERVAL = 30  # seconds for real-time dashboard
DEFAULT_DATE_RANGE = 7  # days

# Page Configuration
PAGE_TITLE = "Retail Analytics Dashboards"
PAGE_ICON = "📊"
LAYOUT = "wide"
