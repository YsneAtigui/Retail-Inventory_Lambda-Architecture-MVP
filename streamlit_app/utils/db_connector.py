"""
Database connector utilities for ClickHouse
"""
import clickhouse_connect
import pandas as pd
import streamlit as st
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


@st.cache_resource
def get_clickhouse_client():
    """
    Create and return a ClickHouse client connection.
    Uses Streamlit caching to maintain a single connection.
    """
    try:
        client = clickhouse_connect.get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            username=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD,
            database=config.CLICKHOUSE_DATABASE
        )
        return client
    except Exception as e:
        st.error(f"Failed to connect to ClickHouse: {str(e)}")
        return None


def execute_query(query: str, use_cache: bool = True) -> Optional[pd.DataFrame]:
    """
    Execute a SQL query and return results as a pandas DataFrame.
    
    Args:
        query: SQL query string
        use_cache: Whether to cache the query results (default: True)
    
    Returns:
        DataFrame with query results or None if error
    """
    client = get_clickhouse_client()
    
    if client is None:
        return None
    
    try:
        if use_cache:
            # Cache queries for 60 seconds
            @st.cache_data(ttl=60)
            def _execute_cached(q):
                result = client.query(q)
                # Return both result set and column names
                return result.result_set, result.column_names
            
            result_set, column_names = _execute_cached(query)
        else:
            result = client.query(query)
            result_set = result.result_set
            column_names = result.column_names
        
        # Convert to DataFrame
        if result_set:
            # Extract column names from the result
            # Handle both tuple format [(name, type)] and string format [name]
            if column_names and isinstance(column_names[0], (tuple, list)):
                columns = [col[0] for col in column_names]
            else:
                columns = column_names
            df = pd.DataFrame(result_set, columns=columns)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Query execution failed: {str(e)}")
        st.code(query, language='sql')
        return None


def get_table_list() -> list:
    """
    Get list of all tables and views in the database.
    
    Returns:
        List of table/view names
    """
    query = """
    SELECT name 
    FROM system.tables 
    WHERE database = '{}'
    ORDER BY name
    """.format(config.CLICKHOUSE_DATABASE)
    
    df = execute_query(query)
    if df is not None and not df.empty:
        return df['name'].tolist()
    return []


def test_connection() -> bool:
    """
    Test if ClickHouse connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    client = get_clickhouse_client()
    if client is None:
        return False
    
    try:
        result = client.query("SELECT 1")
        return True
    except:
        return False


def get_data_freshness() -> dict:
    """
    Get information about data freshness (most recent records).
    
    Returns:
        Dictionary with freshness information
    """
    query = """
    SELECT 
        max(event_time) as latest_event,
        count() as total_records,
        max(inserted_at) as latest_insert
    FROM retail_events_realtime
    """
    
    df = execute_query(query)
    if df is not None and not df.empty:
        return {
            'latest_event': df['latest_event'].iloc[0],
            'total_records': df['total_records'].iloc[0],
            'latest_insert': df['latest_insert'].iloc[0]
        }
    return {}
