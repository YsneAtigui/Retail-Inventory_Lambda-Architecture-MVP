"""
Reusable chart creation utilities using Plotly
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def create_line_chart(df: pd.DataFrame, x: str, y: str, title: str, 
                      color: str = None, height: int = 400) -> go.Figure:
    """
    Create a Plotly line chart.
    
    Args:
        df: DataFrame with data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        color: Optional column for color grouping
        height: Chart height in pixels
    
    Returns:
        Plotly figure object
    """
    fig = px.line(
        df, 
        x=x, 
        y=y, 
        color=color,
        title=title,
        template=config.PLOTLY_TEMPLATE,
        color_discrete_sequence=config.CHART_COLORS
    )
    
    fig.update_layout(
        height=height,
        hovermode='x unified',
        showlegend=True if color else False
    )
    
    return fig


def create_bar_chart(df: pd.DataFrame, x: str, y: str, title: str,
                     orientation: str = 'v', height: int = 400) -> go.Figure:
    """
    Create a Plotly bar chart.
    
    Args:
        df: DataFrame with data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        orientation: 'v' for vertical, 'h' for horizontal
        height: Chart height in pixels
    
    Returns:
        Plotly figure object
    """
    fig = px.bar(
        df,
        x=x if orientation == 'v' else y,
        y=y if orientation == 'v' else x,
        title=title,
        template=config.PLOTLY_TEMPLATE,
        color_discrete_sequence=config.CHART_COLORS,
        orientation=orientation
    )
    
    fig.update_layout(height=height)
    
    return fig


def create_pie_chart(df: pd.DataFrame, values: str, names: str, title: str,
                    height: int = 400, hole: float = 0.4) -> go.Figure:
    """
    Create a Plotly pie/donut chart.
    
    Args:
        df: DataFrame with data
        values: Column name for values
        names: Column name for labels
        title: Chart title
        height: Chart height in pixels
        hole: Size of center hole (0 for pie, >0 for donut)
    
    Returns:
        Plotly figure object
    """
    fig = px.pie(
        df,
        values=values,
        names=names,
        title=title,
        template=config.PLOTLY_TEMPLATE,
        color_discrete_sequence=config.CHART_COLORS,
        hole=hole
    )
    
    fig.update_layout(height=height)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    
    return fig


def create_heatmap(df: pd.DataFrame, x: str, y: str, z: str, title: str,
                  height: int = 400, colorscale: str = 'Viridis') -> go.Figure:
    """
    Create a Plotly heatmap.
    
    Args:
        df: DataFrame with data
        x: Column name for x-axis
        y: Column name for y-axis
        z: Column name for values
        title: Chart title
        height: Chart height in pixels
        colorscale: Plotly colorscale name
    
    Returns:
        Plotly figure object
    """
    # Pivot data for heatmap
    pivot_df = df.pivot(index=y, columns=x, values=z)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale=colorscale,
        hoverongaps=False
    ))
    
    fig.update_layout(
        title=title,
        template=config.PLOTLY_TEMPLATE,
        height=height
    )
    
    return fig


def create_scatter_chart(df: pd.DataFrame, x: str, y: str, title: str,
                        size: str = None, color: str = None, 
                        height: int = 400) -> go.Figure:
    """
    Create a Plotly scatter chart.
    
    Args:
        df: DataFrame with data
        x: Column name for x-axis
        y: Column name for y-axis
        title: Chart title
        size: Optional column for bubble size
        color: Optional column for color grouping
        height: Chart height in pixels
    
    Returns:
        Plotly figure object
    """
    fig = px.scatter(
        df,
        x=x,
        y=y,
        size=size,
        color=color,
        title=title,
        template=config.PLOTLY_TEMPLATE,
        color_discrete_sequence=config.CHART_COLORS
    )
    
    fig.update_layout(height=height)
    
    return fig


def create_kpi_card(title: str, value: str, delta: str = None, 
                   delta_color: str = 'normal') -> str:
    """
    Create an HTML/CSS KPI card.
    
    Args:
        title: KPI title
        value: Main value to display
        delta: Optional change indicator
        delta_color: Color style ('normal', 'inverse', 'off')
    
    Returns:
        HTML string
    """
    delta_html = ""
    if delta:
        color = config.SUCCESS_COLOR if delta_color == 'normal' else config.DANGER_COLOR
        delta_html = f'<p style="color: {color}; font-size: 14px; margin: 5px 0 0 0;">{delta}</p>'
    
    html = f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin: 10px 0;
    ">
        <h3 style="color: white; margin: 0; font-size: 16px; font-weight: 500;">{title}</h3>
        <p style="color: white; font-size: 32px; font-weight: bold; margin: 10px 0;">{value}</p>
        {delta_html}
    </div>
    """
    return html


def create_metric_card(title: str, value: str, subtitle: str = "") -> str:
    """
    Create a simple metric card with gradient background.
    
    Args:
        title: Metric title
        value: Value to display
        subtitle: Optional subtitle text
    
    Returns:
        HTML string
    """
    subtitle_html = f'<p style="color: rgba(255,255,255,0.8); font-size: 12px; margin: 5px 0 0 0;">{subtitle}</p>' if subtitle else ""
    
    html = f"""
    <div style="
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    ">
        <p style="color: white; margin: 0; font-size: 14px; opacity: 0.9;">{title}</p>
        <h2 style="color: white; margin: 8px 0; font-size: 28px;">{value}</h2>
        {subtitle_html}
    </div>
    """
    return html
