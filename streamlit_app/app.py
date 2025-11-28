import streamlit as st
import pandas as pd
#from private.core_logic.paths import TRADE_TRACKING_CSV_PATH, IBKR_CSV


# Page config
st.set_page_config(page_title="Trading Dashboard", layout="wide")

# Custom CSS for academic styling
# Custom CSS for academic styling
# Custom CSS for academic styling
st.markdown("""
    <style>
    /* Only target the main content area, not Streamlit's UI */
    .main .block-container {
        font-family: 'Times New Roman', Times, serif;
    }
    
    /* Justify text */
    .justified-text {
        text-align: justify;
        text-justify: inter-word;
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 18px !important;
    }
    
    /* Title styling */
    .main-title {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 48px !important;
        font-weight: bold !important;
        margin-bottom: 10px;
    }
    
    /* Author name */
    .author {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 28px !important;
        font-style: italic;
        margin-bottom: 20px;
        color: #555;
    }
    
    /* Body text */
    p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 18px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Header section - FILL THIS OUT YOURSELF
st.markdown('<p class="main-title">Systematic Trading Algorithm Performance Analysis</p>', unsafe_allow_html=True)
st.markdown('<p class="author">Oliver Webb - 2025-11-28</p>', unsafe_allow_html=True)

st.markdown("""
<div class="justified-text">
This dashboard presents a summary of the performance of my trading algorithm.

  
I have changed brokers from IBKR to Alpaca, here we inspect the performance of the algorithm on trade logs from Alpaca and IBKR.
  
Trade logs are included in Github, for your own analysis, although certain columns are redacted (trade execution time, asset symbols).

Use the dropdown to select the broker.
</div>
""", unsafe_allow_html=True)

st.markdown("---")  # Horizontal line separator


# Broker selection
broker = st.selectbox(
    "Select Brokerage",
    ["Alpaca", "IBKR"]
)

# Load the appropriate CSV
if broker == "Alpaca":
    df = pd.read_csv("data/trades.csv")
    # Normalize column names for easier analysis
    df['date'] = pd.to_datetime(df['sell_time']).dt.date
    df['pnl'] = df['pnl_amount']
    df['pnl_pct'] = df['pnl_percentage']
    
else:  # IBKR
    df = pd.read_csv("data/ibkr_trades.csv")
    # Normalize column names
    df['date'] = pd.to_datetime(df['trade_date'])
    df['pnl'] = df['FifoPnlRealized']
    # Calculate pnl_pct if you want (would need more info)
    
# Display raw data
st.subheader(f"📋 {broker} Trade Log")
st.dataframe(df, use_container_width=True)

# Basic metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_trades = len(df)
    st.metric("Total Trades", total_trades)

with col2:
    total_pnl = df['pnl'].sum()
    st.metric("Total P&L", f"${total_pnl:.2f}")

with col3:
    wins = (df['pnl'] > 0).sum()
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    st.metric("Win Rate", f"{win_rate:.1f}%")

with col4:
    avg_pnl = df['pnl'].mean()
    st.metric("Avg P&L", f"${avg_pnl:.2f}")

# Simple chart
st.subheader("📈 Cumulative P&L")
df_sorted = df.sort_values('date')
df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
st.line_chart(df_sorted.set_index('date')['cumulative_pnl'])