"""
Stock Market Anomaly Detection Dashboard
==========================================
Interactive Streamlit dashboard for visualizing and analyzing anomalies in Tunisian stock market data.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# Import utility functions
import anomaly_utils

# Page configuration
st.set_page_config(
    page_title="Stock Anomaly Detection Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark mode styling
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1a1d29;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #00d4ff;
        font-weight: 600;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #00d4ff;
        font-size: 28px;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #00d4ff;
        color: #0e1117;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #00a8cc;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
    }
    
    /* Select boxes */
    .stSelectbox [data-baseweb="select"] {
        background-color: #262b3d;
    }
    
    /* Date inputs */
    .stDateInput [data-baseweb="input"] {
        background-color: #262b3d;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #1a1d29;
        border-left: 4px solid #00d4ff;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Anomaly details card */
    .anomaly-card {
        background: linear-gradient(135deg, #1a1d29 0%, #262b3d 100%);
        border: 1px solid #00d4ff;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0, 212, 255, 0.2);
    }
    
    /* Divider */
    hr {
        border-color: #00d4ff;
        opacity: 0.3;
    }
    </style>
""", unsafe_allow_html=True)


def create_price_volume_charts(data, stock_name):
    """
    Create interactive Plotly charts for price and volume with anomaly markers.
    
    Args:
        data (pd.DataFrame): Filtered stock data
        stock_name (str): Name of the stock for title
    
    Returns:
        plotly.graph_objects.Figure: Interactive figure with subplots
    """
    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{stock_name} - Closing Price', f'{stock_name} - Trading Volume'),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5]
    )
    
    # Sort data by date to ensure proper line plotting
    data = data.sort_values('SEANCE').reset_index(drop=True)
    
    # Get anomaly data points
    anomaly_data = data[data['ANOMALY'] == 1]
    
    # ========== CLOSING PRICE CHART ==========
    # Plot ALL data as a continuous line (not just normal data)
    fig.add_trace(
        go.Scatter(
            x=data['SEANCE'],
            y=data['CLOTURE'],
            mode='lines',
            name='Close Price',
            line=dict(color='#00d4ff', width=2),
            hovertemplate='<b>Date:</b> %{x|%Y-%m-%d}<br><b>Close:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Anomaly markers - red circles overlaid on the line
    if len(anomaly_data) > 0:
        fig.add_trace(
            go.Scatter(
                x=anomaly_data['SEANCE'],
                y=anomaly_data['CLOTURE'],
                mode='markers',
                name='Anomaly',
                marker=dict(
                    color='#ff4444',
                    size=14,
                    symbol='circle',
                    line=dict(color='#cc0000', width=2)
                ),
                hovertemplate='<b>🚨 ANOMALY</b><br><b>Date:</b> %{x|%Y-%m-%d}<br><b>Close:</b> %{y:.2f}<br><b>Score:</b> %{customdata:.1f}<extra></extra>',
                customdata=anomaly_data['ANOMALY_SCORE']
            ),
            row=1, col=1
        )
    
    # ========== VOLUME CHART ==========
    # Plot ALL volume data as line (like the notebook version)
    fig.add_trace(
        go.Scatter(
            x=data['SEANCE'],
            y=data['QUANTITE_NEGOCIEE'],
            mode='lines',
            name='Volume',
            line=dict(color='#00ff88', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 136, 0.3)',
            hovertemplate='<b>Date:</b> %{x|%Y-%m-%d}<br><b>Volume:</b> %{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Anomaly markers on volume - at the actual volume values
    if len(anomaly_data) > 0:
        fig.add_trace(
            go.Scatter(
                x=anomaly_data['SEANCE'],
                y=anomaly_data['QUANTITE_NEGOCIEE'],
                mode='markers',
                name='Anomaly (Volume)',
                marker=dict(
                    color='#ff4444',
                    size=14,
                    symbol='circle',
                    line=dict(color='#cc0000', width=2)
                ),
                hovertemplate='<b>🚨 ANOMALY</b><br><b>Date:</b> %{x|%Y-%m-%d}<br><b>Volume:</b> %{y:,.0f}<br><b>Score:</b> %{customdata:.1f}<extra></extra>',
                customdata=anomaly_data['ANOMALY_SCORE'],
                showlegend=False
            ),
            row=2, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='x unified',
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff', size=12),
        legend=dict(
            bgcolor='#1a1d29',
            bordercolor='#00d4ff',
            borderwidth=1
        ),
        margin=dict(l=60, r=60, t=80, b=60)
    )
    
    # Update axes
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#262b3d',
        showline=True,
        linecolor='#00d4ff',
        linewidth=1
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridcolor='#262b3d',
        showline=True,
        linecolor='#00d4ff',
        linewidth=1
    )
    
    # Update subplot titles
    fig.update_annotations(font=dict(color='#00d4ff', size=14))
    
    return fig


def display_anomaly_details(details):
    """Display detailed information about a selected anomaly."""
    st.markdown("### 🔍 Anomaly Details")
    
    # Create columns for organized display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📊 Price Information")
        st.metric("Opening Price", f"{details['OUVERTURE']:.2f}")
        st.metric("Closing Price", f"{details['CLOTURE']:.2f}")
        st.metric("Highest Price", f"{details['PLUS_HAUT']:.2f}")
        st.metric("Lowest Price", f"{details['PLUS_BAS']:.2f}")
    
    with col2:
        st.markdown("#### 💰 Trading Activity")
        st.metric("Volume", f"{int(details['QUANTITE_NEGOCIEE']):,}")
        st.metric("Transactions", f"{int(details['NB_TRANSACTION']):,}")
        st.metric("Capital Traded", f"{details['CAPITAUX']:,.2f}")
        st.metric("Avg Trade Size", f"{details.get('Avg_Trade_Size', 0):.2f}")
    
    with col3:
        st.markdown("#### 🚨 Anomaly Metrics")
        st.metric("Anomaly Score", f"{details['ANOMALY_SCORE']:.2f}")
        st.metric("Daily Return %", f"{details.get('Daily_Return_Pct', 0):.2f}%")
        st.metric("Intraday Range %", f"{details.get('Intraday_Range_Pct', 0):.2f}%")
        st.metric("Price Position", f"{details.get('Price_Position', 0):.3f}")


def main():
    """Main application function."""
    
    # Header
    st.title("📈 Stock Market Anomaly Detection Dashboard")
    st.markdown("---")
    
    # Get all available codes and mappings (dataset loaded in anomaly_utils)
    all_codes = anomaly_utils.get_all_codes()
    code_mapping = anomaly_utils.get_code_name_mapping()
    
    # ========== SIDEBAR FILTERS ==========
    with st.sidebar:
        st.markdown("## 🎯 Filter Options")
        st.markdown("---")
        
        # Stock selection
        st.markdown("### 📌 Select Stock")
        selected_code = st.selectbox(
            "Ticker Code",
            options=all_codes,
            format_func=lambda x: f"{x} - {code_mapping.get(x, 'Unknown')}",
            help="Choose a stock ticker to analyze"
        )
        
        stock_name = code_mapping.get(selected_code, selected_code)
        st.info(f"**Selected:** {stock_name}")
        
        st.markdown("---")
        
        # Date range selection
        st.markdown("### 📅 Date Range")
        
        try:
            min_date, max_date = anomaly_utils.get_available_date_range(selected_code)
            
            # Convert to date objects for date_input
            min_date_obj = min_date.date() if hasattr(min_date, 'date') else min_date
            max_date_obj = max_date.date() if hasattr(max_date, 'date') else max_date
            
            st.caption(f"Available: {min_date_obj} to {max_date_obj}")
            
            start_date = st.date_input(
                "Start Date",
                value=min_date_obj,
                min_value=min_date_obj,
                max_value=max_date_obj
            )
            
            end_date = st.date_input(
                "End Date",
                value=max_date_obj,
                min_value=min_date_obj,
                max_value=max_date_obj
            )
            
            # Validate date range
            if start_date > end_date:
                st.error("⚠️ Start date must be before end date!")
                st.stop()
            
        except ValueError as e:
            st.error(f"Error loading date range: {e}")
            st.stop()
        
        st.markdown("---")
        
        # Confirm button
        confirm_button = st.button("🔍 Analyze", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        
        # Always show summary stats
        try:
            summary = anomaly_utils.get_anomaly_summary_for_code(
                selected_code,
                pd.Timestamp(start_date),
                pd.Timestamp(end_date)
            )
            
            st.metric("Total Days", f"{summary['total_days']}")
            st.metric("Anomalies", f"{summary['anomaly_days']}")
            st.metric("Anomaly Rate", f"{summary['anomaly_percentage']:.1f}%")
            
        except Exception as e:
            st.warning(f"Stats unavailable: {e}")
    
    # ========== MAIN CONTENT AREA ==========
    
    if confirm_button or 'data_loaded' in st.session_state:
        st.session_state['data_loaded'] = True
        
        try:
            # Get filtered data
            data = anomaly_utils.get_stock_data_filtered(
                selected_code,
                pd.Timestamp(start_date),
                pd.Timestamp(end_date)
            )
            
            if len(data) == 0:
                st.warning("⚠️ No data available for the selected date range.")
                st.stop()
            
            # Display summary
            st.markdown(f"## 📊 Analysis: {stock_name}")
            st.markdown(f"**Period:** {start_date} to {end_date} ({len(data)} trading days)")
            
            # Create and display charts
            with st.spinner("Generating charts..."):
                fig = create_price_volume_charts(data, stock_name)
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Anomaly inspection section
            anomaly_data = data[data['ANOMALY'] == 1]
            
            if len(anomaly_data) > 0:
                st.markdown("## 🚨 Detected Anomalies")
                st.markdown(f"**{len(anomaly_data)} anomalous days detected** (click on date to see details)")
                
                # Display anomaly dates as clickable buttons
                st.markdown("### Select Anomaly Date:")
                
                # Create columns for date buttons (5 per row)
                dates_list = anomaly_data['SEANCE'].dt.date.tolist()
                num_cols = 5
                rows = [dates_list[i:i+num_cols] for i in range(0, len(dates_list), num_cols)]
                
                for row in rows:
                    cols = st.columns(num_cols)
                    for idx, date in enumerate(row):
                        with cols[idx]:
                            if st.button(str(date), key=f"date_{date}", use_container_width=True):
                                st.session_state['selected_anomaly_date'] = pd.Timestamp(date)
                
                # Display details if a date is selected
                if 'selected_anomaly_date' in st.session_state:
                    st.markdown("---")
                    selected_date = st.session_state['selected_anomaly_date']
                    
                    try:
                        details = anomaly_utils.get_anomaly_details(selected_code, selected_date)
                        
                        st.markdown(f"### 📅 {selected_date.date()}")
                        display_anomaly_details(details)
                        
                    except Exception as e:
                        st.error(f"Error loading anomaly details: {e}")
            
            else:
                st.info("✅ No anomalies detected in the selected date range.")
        
        except Exception as e:
            st.error(f"❌ Error loading data: {e}")
            st.exception(e)
    
    else:
        # Initial state - show welcome message
        st.markdown("""
        ### 👋 Welcome to the Stock Anomaly Detection Dashboard
        
        This dashboard helps you visualize and analyze unusual patterns in stock market data.
        
        **How to use:**
        1. 📌 Select a stock ticker from the sidebar
        2. 📅 Choose your date range
        3. 🔍 Click "Analyze" to generate charts
        4. 🚨 Click on anomaly dates to see detailed information
        
        **Features:**
        - Interactive price and volume charts
        - Anomaly detection using Isolation Forest
        - Detailed metrics for each anomaly day
        - Dark mode interface for comfortable viewing
        """)
        
        st.info("👈 Use the sidebar to get started!")


if __name__ == "__main__":
    main()
