"""
Business metrics calculation utilities
"""
import pandas as pd
from typing import Union


def calculate_revenue_metrics(df: pd.DataFrame, revenue_col: str = 'total_revenue') -> dict:
    """
    Calculate revenue-related metrics from a DataFrame.
    
    Args:
        df: DataFrame with revenue data
        revenue_col: Name of the revenue column
    
    Returns:
        Dictionary with metrics
    """
    if df.empty or revenue_col not in df.columns:
        return {
            'total_revenue': 0,
            'avg_revenue': 0,
            'max_revenue': 0,
            'min_revenue': 0
        }
    
    return {
        'total_revenue': df[revenue_col].sum(),
        'avg_revenue': df[revenue_col].mean(),
        'max_revenue': df[revenue_col].max(),
        'min_revenue': df[revenue_col].min()
    }


def calculate_performance_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate general performance metrics.
    
    Args:
        df: DataFrame with transaction data
    
    Returns:
        Dictionary with metrics
    """
    if df.empty:
        return {
            'total_transactions': 0,
            'unique_products': 0,
            'unique_stores': 0
        }
    
    metrics = {
        'total_transactions': len(df)
    }
    
    if 'product_id' in df.columns:
        metrics['unique_products'] = df['product_id'].nunique()
    
    if 'store_id' in df.columns:
        metrics['unique_stores'] = df['store_id'].nunique()
    
    return metrics


def format_currency(value: Union[int, float], currency: str = '$') -> str:
    """
    Format a number as currency.
    
    Args:
        value: Numeric value
        currency: Currency symbol (default: '$')
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return f"{currency}0"
    
    if abs(value) >= 1_000_000:
        return f"{currency}{value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{currency}{value/1_000:.2f}K"
    else:
        return f"{currency}{value:.2f}"


def format_percentage(value: Union[int, float], decimals: int = 1) -> str:
    """
    Format a number as percentage.
    
    Args:
        value: Numeric value (0-100 or 0-1)
        decimals: Number of decimal places
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "0%"
    
    # If value is between 0 and 1, assume it's a ratio and convert to percentage
    if 0 <= abs(value) <= 1:
        value = value * 100
    
    return f"{value:.{decimals}f}%"


def format_number(value: Union[int, float], decimals: int = 0) -> str:
    """
    Format a large number with K/M/B suffixes.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "0"
    
    if abs(value) >= 1_000_000_000:
        return f"{value/1_000_000_000:.{decimals}f}B"
    elif abs(value) >= 1_000_000:
        return f"{value/1_000_000:.{decimals}f}M"
    elif abs(value) >= 1_000:
        return f"{value/1_000:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"


def calculate_growth_rate(current: float, previous: float) -> float:
    """
    Calculate growth rate between two values.
    
    Args:
        current: Current period value
        previous: Previous period value
    
    Returns:
        Growth rate as percentage
    """
    if previous == 0:
        return 0 if current == 0 else 100
    
    return ((current - previous) / previous) * 100
