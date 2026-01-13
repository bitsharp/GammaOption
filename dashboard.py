"""Streamlit dashboard for real-time ES level monitoring."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date
import json
from pathlib import Path
import time
from config import config
from data_fetcher import DataFetcher
from gamma_engine import GammaEngine
from es_converter import SPXtoESConverter
from alert_system import AlertSystem
from loguru import logger


# Page configuration
st.set_page_config(
    page_title="Gamma Option Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .big-font {
        font-size: 40px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .alert-box {
        background-color: #ff4444;
        color: white;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        font-weight: bold;
    }
    .success-box {
        background-color: #00cc66;
        color: white;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_components():
    """Initialize all components (cached)."""
    return {
        'fetcher': DataFetcher(),
        'engine': GammaEngine(),
        'converter': SPXtoESConverter(),
        'alerts': AlertSystem()
    }


def load_latest_data():
    """Load the latest calculated data from files."""
    data_dir = Path(config.data_dir)
    
    # Try to load cached levels
    levels_file = data_dir / "latest_levels.json"
    if levels_file.exists():
        with open(levels_file, 'r') as f:
            return json.load(f)
    
    return None


def create_level_chart(es_price, converted_levels, regime):
    """Create interactive chart with ES price and gamma levels.
    
    Args:
        es_price: Current ES price
        converted_levels: Dictionary with converted levels
        regime: Market regime
    """
    fig = go.Figure()
    
    # Extract levels for plotting
    levels = []
    names = []
    colors = []
    
    for level_name, level_data in converted_levels.items():
        if 'es' in level_data:
            levels.append(level_data['es'])
            names.append(level_name.replace('_', ' ').title())
            
            # Color coding
            if 'put' in level_name.lower():
                colors.append('green')
            elif 'call' in level_name.lower():
                colors.append('red')
            else:
                colors.append('blue')
    
    # Add horizontal lines for each level
    for level, name, color in zip(levels, names, colors):
        fig.add_hline(
            y=level,
            line_dash="dash",
            line_color=color,
            annotation_text=f"{name}: ${level:.2f}",
            annotation_position="right"
        )
    
    # Add current price
    fig.add_hline(
        y=es_price,
        line_width=3,
        line_color="black",
        annotation_text=f"ES: ${es_price:.2f}",
        annotation_position="left"
    )
    
    # Update layout
    fig.update_layout(
        title=f"ES Gamma Levels - {regime.upper()}",
        yaxis_title="ES Price",
        height=600,
        showlegend=False,
        hovermode='y'
    )
    
    return fig


def main():
    """Main dashboard function."""
    
    # Title
    st.title("📊 Gamma Option Dashboard")
    st.markdown("### ES Future Levels Based on SPX 0DTE Gamma Exposure")
    
    # Initialize components
    components = initialize_components()
    fetcher = components['fetcher']
    converter = components['converter']
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()
        
        st.divider()
        
        # Configuration display
        st.subheader("Configuration")
        st.text(f"Strike Range: ±{config.strike_range_percent}%")
        st.text(f"Min Volume: {config.min_volume_threshold}")
        st.text(f"Alert Threshold: ±{config.alert_distance_threshold} pts")
        
        st.divider()
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
        
    # Main content
    try:
        # Get current prices
        col1, col2, col3 = st.columns(3)
        
        with col1:
            with st.spinner("Fetching SPX price..."):
                spx_price = fetcher.get_spx_price()
                if spx_price:
                    st.metric("SPX Price", f"${spx_price:.2f}")
                else:
                    st.error("SPX price unavailable")
        
        with col2:
            with st.spinner("Fetching ES price..."):
                es_price = fetcher.get_es_price()
                if es_price:
                    st.metric("ES Price", f"${es_price:.2f}")
                else:
                    st.error("ES price unavailable")
        
        with col3:
            if spx_price and es_price:
                spread = converter.get_spread()
                if spread is None:
                    spread = es_price - spx_price
                    converter.calculate_spread(spx_price, es_price)
                
                st.metric("ES-SPX Spread", f"{spread:+.2f}")
        
        st.divider()
        
        # Load latest data
        latest_data = load_latest_data()
        
        if latest_data:
            converted_levels = latest_data.get('converted_levels', {})
            regime = latest_data.get('regime', 'unknown')
            
            # Display regime
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("Market Regime")
                if regime == "long_gamma":
                    st.success("🟢 LONG GAMMA - Expect mean reversion, lower volatility")
                elif regime == "short_gamma":
                    st.error("🔴 SHORT GAMMA - Expect higher volatility, trending moves")
                else:
                    st.info("⚪ NEUTRAL")
            
            with col2:
                st.subheader("Last Update")
                update_time = latest_data.get('timestamp', 'Unknown')
                st.text(update_time)
            
            st.divider()
            
            # Key levels
            st.subheader("🎯 Key Gamma Levels")
            
            cols = st.columns(len(converted_levels))
            
            for idx, (level_name, level_data) in enumerate(converted_levels.items()):
                with cols[idx]:
                    st.markdown(f"**{level_name.replace('_', ' ').title()}**")
                    st.metric(
                        label="ES Level",
                        value=f"${level_data['es']:.2f}",
                        delta=f"SPX: ${level_data['spx']:.2f}"
                    )
                    
                    # Distance to current price
                    if es_price:
                        distance = es_price - level_data['es']
                        st.text(f"Distance: {distance:+.2f}")
            
            st.divider()
            
            # Chart
            if es_price:
                st.subheader("📈 ES Price vs Gamma Levels")
                chart = create_level_chart(es_price, converted_levels, regime)
                st.plotly_chart(chart, use_container_width=True)
            
            st.divider()
            
            # Alerts section
            st.subheader("🚨 Recent Alerts")
            
            alert_log_file = config.logs_dir / "alerts.jsonl"
            if alert_log_file.exists():
                # Read last 10 alerts
                alerts = []
                with open(alert_log_file, 'r') as f:
                    for line in f:
                        alerts.append(json.loads(line))
                
                if alerts:
                    # Display most recent alerts
                    for alert in alerts[-5:]:
                        st.markdown(f"""
                        <div class="alert-box">
                        🚨 {alert['level_name'].upper()} @ ${alert['es_level']:.2f}<br>
                        Current: ${alert['current_price']:.2f} | Distance: ${alert['distance']:.2f}<br>
                        {alert['timestamp']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No alerts triggered yet today")
            else:
                st.info("No alerts triggered yet today")
            
        else:
            st.warning("⚠️ No data available. Run the main application to fetch and calculate levels.")
            
            if st.button("Run Data Fetch Now"):
                with st.spinner("Fetching data and calculating levels..."):
                    st.info("Please run: python main.py")
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        logger.error(f"Dashboard error: {e}")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()
