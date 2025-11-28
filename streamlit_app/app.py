import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px


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

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ... your existing CSS and header code ...

# Broker selection
broker = st.selectbox("Select Brokerage", ["Alpaca", "IBKR"])

# Load and normalize data
if broker == "Alpaca":
    df = pd.read_csv("data/trades.csv")
    df['date'] = pd.to_datetime(df['sell_time'])
    df['pnl'] = df['pnl_amount']
else:  # IBKR
    df = pd.read_csv("data/ibkr_trades.csv")
    df['date'] = pd.to_datetime(df['trade_date'])
    df['pnl'] = df['FifoPnlRealized']
    df['basis'] = df['CostBasis']

df = df.sort_values('date')

# Calculate metrics
total_pnl = df['pnl'].sum()
num_trades = len(df)
wins = (df['pnl'] > 0).sum()
losses = (df['pnl'] < 0).sum()
win_rate = (wins / num_trades * 100) if num_trades > 0 else 0

# Calculate cumulative P&L
df['cumulative_pnl'] = df['pnl'].cumsum()

# CORRECTED: Aggregate to daily returns for Sharpe ratio
daily_pnl = df.groupby(df['date'].dt.date)['pnl'].sum()

# Calculate daily returns as percentage of running capital
# Assume starting capital (you can adjust this)
starting_capital = 10000  
daily_capital = starting_capital + daily_pnl.cumsum()
daily_returns = daily_pnl / daily_capital.shift(1).fillna(starting_capital)

# Sharpe ratio (annualized, assuming 252 trading days)
sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0

# Max drawdown (from cumulative P&L)
cumulative = df['cumulative_pnl']
running_max = cumulative.cummax()
drawdown = cumulative - running_max
max_drawdown = drawdown.min()

st.markdown("---")

# SECTION 1: Hero Metrics
st.markdown("### Performance Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Return", f"${total_pnl:,.2f}")

with col2:
    st.metric("Win Rate", f"{win_rate:.1f}%", f"{wins}W / {losses}L")

with col3:
    st.metric("Sharpe Ratio", f"{sharpe:.2f}")

with col4:
    st.metric("Max Drawdown", f"${max_drawdown:,.2f}")

st.markdown("---")

# SECTION 2: Core Visualizations
st.markdown("### Performance Analysis")
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Equity Curve**")
    fig_equity = go.Figure()
    fig_equity.add_trace(go.Scatter(
        x=df['date'],
        y=df['cumulative_pnl'],
        mode='lines',
        line=dict(color='#2E86AB', width=2),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.1)'
    ))
    fig_equity.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Times New Roman, Times, serif")
    )
    st.plotly_chart(fig_equity, use_container_width=True)

with col_right:
    st.markdown("**Returns Distribution**")
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=df['pnl'],
        nbinsx=30,
        marker=dict(color='#A23B72', line=dict(color='white', width=1))
    ))
    fig_dist.update_layout(
        xaxis_title="Trade P&L ($)",
        yaxis_title="Frequency",
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Times New Roman, Times, serif")
    )
    st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("---")

# SECTION 3: Trade Statistics
st.markdown("### Detailed Statistics")
stat_col1, stat_col2, stat_col3 = st.columns(3)

with stat_col1:
    st.markdown("**Trade Summary**")
    avg_pnl = df['pnl'].mean()
    best_trade = df['pnl'].max()
    worst_trade = df['pnl'].min()
    
    st.write(f"Total Trades: {num_trades}")
    st.write(f"Avg P&L: ${avg_pnl:.2f}")
    st.write(f"Best Trade: ${best_trade:.2f}")
    st.write(f"Worst Trade: ${worst_trade:.2f}")

with stat_col2:
    st.markdown("**Monthly Performance**")
    df['month'] = df['date'].dt.to_period('M')
    monthly = df.groupby('month')['pnl'].sum().reset_index()
    monthly['month'] = monthly['month'].astype(str)
    
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Bar(
        x=monthly['month'],
        y=monthly['pnl'],
        marker_color=['green' if x > 0 else 'red' for x in monthly['pnl']]
    ))
    fig_monthly.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

with stat_col3:
    st.markdown("**Risk Metrics**")
    volatility = returns.std() * np.sqrt(252) * 100
    profit_factor = df[df['pnl'] > 0]['pnl'].sum() / abs(df[df['pnl'] < 0]['pnl'].sum()) if losses > 0 else np.inf
    
    # Max consecutive losses
    df['is_loss'] = df['pnl'] < 0
    df['loss_streak'] = df['is_loss'].groupby((df['is_loss'] != df['is_loss'].shift()).cumsum()).cumsum()
    max_consecutive_losses = df['loss_streak'].max()
    
    st.write(f"Volatility: {volatility:.1f}%")
    st.write(f"Profit Factor: {profit_factor:.2f}")
    st.write(f"Max Consecutive Losses: {int(max_consecutive_losses)}")

st.markdown("---")

# SECTION 4: Raw Data
with st.expander("📋 View Detailed Trade Log"):
    st.dataframe(df[['date', 'pnl']].reset_index(drop=True), use_container_width=True)