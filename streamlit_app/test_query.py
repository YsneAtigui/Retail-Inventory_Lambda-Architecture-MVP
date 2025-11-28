"""
Quick test script to verify database connection and query execution
"""
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from utils.db_connector import execute_query

# Test the KPI query
kpi_query = """
SELECT
    count() as total_transactions,
    sum(quantity * unit_price) as total_revenue,
    avg(quantity * unit_price) as avg_basket_value,
    sum(quantity) as total_quantity
FROM retail_events_realtime
WHERE transaction_type = 'SALE'
    AND event_time >= now() - INTERVAL 24 HOUR
"""

print("Testing KPI query...")
print("-" * 50)

df_kpi = execute_query(kpi_query, use_cache=False)

if df_kpi is not None and not df_kpi.empty:
    print("Query executed successfully!")
    print("\nDataFrame columns:", df_kpi.columns.tolist())
    print("\nDataFrame shape:", df_kpi.shape)
    print("\nDataFrame content:")
    print(df_kpi)
    print("\n" + "-" * 50)
    
    # Try to access the columns
    try:
        total_revenue = float(df_kpi['total_revenue'].iloc[0])
        total_transactions = int(df_kpi['total_transactions'].iloc[0])
        avg_basket = float(df_kpi['avg_basket_value'].iloc[0])
        total_qty = int(df_kpi['total_quantity'].iloc[0])
        
        print("\n✓ Successfully accessed all columns:")
        print(f"  - Total Revenue: ${total_revenue:,.2f}")
        print(f"  - Total Transactions: {total_transactions:,}")
        print(f"  - Avg Basket Value: ${avg_basket:,.2f}")
        print(f"  - Total Quantity: {total_qty:,}")
    except KeyError as e:
        print(f"\n✗ KeyError: {e}")
        print("Available columns:", df_kpi.columns.tolist())
else:
    print("Query failed or returned no data!")
