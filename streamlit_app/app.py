import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "data"

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

st.markdown('<p class="main-title">Systematic Trading Algorithm Performance Analysis</p>', unsafe_allow_html=True)
st.markdown('<p class="author">Oliver Webb - 2025-12-01</p>', unsafe_allow_html=True)

st.markdown("### About This Dashboard")
st.markdown("I developed a trading algorithm, the results of which are displayed here. A complete end to end build, I started running it on Interactive Brokers in July 2025. Changes have been made since; most recently: I have moved brokers to Alpaca - as they offer a more flexible API for headless trading.")
st.markdown("So far this is all paper trading, with no real money at stake.")

st.markdown("You can select which results to view: the few months of trading with IBKR, and the short while it has been running with Alpaca.")



def get_sp500_return_for_trade(row):
    buy_date = row['buy_date_dt'].date() if hasattr(row['buy_date_dt'], 'date') else row['buy_date_dt']
    sell_date = row['sell_date_dt'].date() if hasattr(row['sell_date_dt'], 'date') else row['sell_date_dt']
    
    available_dates = sp500_daily.index
    
    buy_dates_before = [d for d in available_dates if d <= buy_date]
    if not buy_dates_before:
        return np.nan
    buy_price_date = max(buy_dates_before)
    
    sell_dates_before = [d for d in available_dates if d <= sell_date]
    if not sell_dates_before:
        return np.nan
    sell_price_date = max(sell_dates_before)
    
    buy_price = sp500_daily.loc[buy_price_date, 'sp500_close']
    sell_price = sp500_daily.loc[sell_price_date, 'sp500_close']
    
    if buy_price == 0 or pd.isna(buy_price):
        return np.nan
    
    return ((sell_price - buy_price) / buy_price) * 100



# Broker selection
broker = st.selectbox("", ["Alpaca", "IBKR"])

# Load and normalize data
if broker == "Alpaca":
    df = pd.read_csv(DATA_DIR / "trades.csv")
    df['buy_date_dt'] = pd.to_datetime(df['buy_time'])
    df['sell_date_dt'] = pd.to_datetime(df['sell_time'])
    df['date'] = df['sell_date_dt']  # Use sell date as the reference date
    df['pnl'] = df['pnl_amount']
    df['basis'] = df['basis']
    df['return_pct'] = df['pnl'] / df['basis']  # Compute return_pct for per-trade comparison
    capital = 5000 # average deployed capital, certain assumptions made here
elif broker == "IBKR":
    df = pd.read_csv(DATA_DIR / "ibkr_trades_round_trips.csv")
    df['buy_date_dt'] = pd.to_datetime(df['buy_date_dt'])
    df['sell_date_dt'] = pd.to_datetime(df['sell_date_dt'])
    df['date'] = df['sell_date_dt']  # Use sell date as the reference date
    df['pnl'] = df['pnl']
    df['basis'] = df['basis']
    # return_pct should already exist in IBKR csv
    capital = 200000 # average deployed capital, certain assumptions made here




### ============================================= ###
#                      METRICS                      #
### ============================================= ###


df = df.sort_values('date')
df['basis'] = df['basis'].abs()
df['return_pct_individual'] = df['pnl'] / df['basis']

daily = df.groupby('date').agg(
    pnl_daily=('pnl','sum'),
    basis_daily=('basis','sum'))
daily['daily_return_pct'] = daily['pnl_daily'] / daily['basis_daily']

# Download S&P 500 data for comparison (per-trade holding period method)
trade_by_sell_date = None
start_date = df['buy_date_dt'].min() - pd.Timedelta(days=5)
end_date = df['sell_date_dt'].max() + pd.Timedelta(days=5)

sp500 = yf.download('^GSPC', start=start_date, end=end_date, progress=False)

if not sp500.empty and 'Close' in sp500.columns:
    sp500_daily = pd.DataFrame(index=pd.to_datetime(sp500.index).date)
    sp500_daily['sp500_close'] = sp500['Close'].values
    sp500_daily['sp500_return_pct'] = sp500['Close'].pct_change().values * 100
    
    df['sp500_return_trade'] = df.apply(get_sp500_return_for_trade, axis=1)
    
    valid_mask_trade = df['return_pct'].notna() & df['sp500_return_trade'].notna()
    if valid_mask_trade.sum() > 1:
        correlation_with_sp500 = df.loc[valid_mask_trade, 'return_pct'].corr(
            df.loc[valid_mask_trade, 'sp500_return_trade']
        )
    else:
        correlation_with_sp500 = np.nan
    
    # Aggregate by sell_date for rolling correlation
    trade_by_sell_date = df.groupby(df['sell_date_dt'].dt.date).agg(
        return_pct_mean=('return_pct', 'mean'),
        sp500_return_mean=('sp500_return_trade', 'mean')
    ).sort_index()
    
    # Rolling correlation on aggregated data
    window = 40
    trade_by_sell_date['roll_corr_spx'] = (
        trade_by_sell_date['return_pct_mean']
        .rolling(window=window)
        .corr(trade_by_sell_date['sp500_return_mean'])
    )
    
    # Also add daily SP500 data for other charts
    if not isinstance(daily.index[0], type(pd.Timestamp.now().date())):
        daily.index = pd.to_datetime(daily.index).date
    daily = daily.merge(sp500_daily[['sp500_close', 'sp500_return_pct']], 
                        left_index=True, right_index=True, how='left')
else:
    df['sp500_return_trade'] = np.nan
    daily['sp500_close'] = np.nan
    daily['sp500_return_pct'] = np.nan
    correlation_with_sp500 = np.nan

# 1. NUMBER OF TRADES, win rate
num_trades = len(df)


# 2 sharpe by dollar amount
sharpe_dollar = (daily['pnl_daily'].mean() / daily['pnl_daily'].std()) * np.sqrt(252)


# 3 sharpe using capital
daily['equity'] = capital + daily['pnl_daily'].cumsum()
daily['equity_prev'] = daily['equity'].shift(1)
daily['ret_equity'] = daily['equity'] / daily['equity_prev'] - 1
daily.loc[daily.index[0], 'ret_equity'] = (
    daily.iloc[0]['equity'] / capital - 1)

mean_ret = daily['ret_equity'].mean()
std_ret  = daily['ret_equity'].std(ddof=1)
sharpe_capital = np.sqrt(252) * mean_ret / std_ret



# 4 max drawdown
daily['cum_return_pct'] = (1 + daily['daily_return_pct']).cumprod()
daily['peak_cum_return_pct'] = daily['cum_return_pct'].cummax()
daily['drawdown'] = daily['cum_return_pct'] / daily['peak_cum_return_pct'] - 1
max_drawdown_pct = daily['drawdown'].min() * 100

# 5 win rate
wins = (df['pnl'] > 0).sum()
losses = (df['pnl'] < 0).sum()
win_rate = (wins / num_trades * 100) if num_trades > 0 else 0


# 6 average win vs average loss
avg_win = df[df['return_pct_individual'] > 0]['return_pct_individual'].mean() * 100
avg_loss = df[df['return_pct_individual'] < 0]['return_pct_individual'].mean() * 100



# 7 profit factor
gross_profit = df[df['pnl'] > 0]['pnl'].sum()
gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf


# 8 mean return per trade
mean_return_per_trade = df['return_pct_individual'].mean()*100



st.markdown("---")


### ============================================= ###
#                 VISUALISATIONS                    #
### ============================================= ###

# SECTION 1: Hero Metrics
st.markdown("### Performance Metrics")
st.markdown("""
Paper trading accounts allocate large amounts of capital (usually ~\$1M), but deployed capital and position sizing are both much smaller than total bankroll. Hence, no meaningful equity curve exists (since profits from trades do not significantly change the total bankroll). As such, calculating annualised returns is not meaningful. We approximate Sharpe in two ways:
""")

eq_col1, eq_col2 = st.columns(2)
with eq_col1:
    st.latex(r"\text{Sharpe}_{\text{dollar}} = \frac{\bar{P}_d}{\sigma(P_d)} \times \sqrt{252}")
with eq_col2:
    st.latex(r"\text{Sharpe}_{\text{capital}} = \frac{\bar{r}_d}{\sigma(r_d)} \times \sqrt{252}")

st.markdown("""
where $P_d$ is the P&L on day $d$ (in dollars), $r_d = (E_d - E_{d-1}) / E_{d-1}$ is the daily return, and $E_d$ is the equity on day $d$ computed using an assumed initial capital. We note that the Interactive Brokers dashboard indicates a Sharpe of 1.6, although this likely includes risk free interest rate (4.5% in US), and will be based on total account value.
""")

st.markdown("")



col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Number of Trades", f"{num_trades}")

with col2:
    st.metric("Sharpe (Capital / Dollar)", f"{sharpe_capital:.2f} / {sharpe_dollar:.2f}")

with col3:
    st.metric("S&P 500 Correlation", f"{correlation_with_sp500:.2f}")

with col4:
    st.metric("Max Drawdown", f"{max_drawdown_pct:.2f}%")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("Win Rate", f"{win_rate:.1f}%", f"{wins}W / {losses}L")

with col6:
    st.metric("Avg Win / Avg Loss", f"{avg_win:.1f}% / {avg_loss:.1f}%")

with col7:
    st.metric("Profit Factor", f"{profit_factor:.2f}")

with col8:
    st.metric("Mean Return per Trade", f"{mean_return_per_trade:.2f}%")


st.markdown("---")


# SECTION 2: Visualizations
st.markdown("### Performance Analysis")

# First Row: Cumulative P&L and Daily P&L Bar Chart
row1_col1, row1_col2 = st.columns(2, gap="large")

with row1_col1:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Cumulative P&L Over Time</h1>", unsafe_allow_html=True)
    st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)  # Spacer to align with selector
    df['cumulative_pnl'] = df['pnl'].cumsum()
    df['cumulative_trades'] = range(1, len(df) + 1)  # Cumulative count of trades
    fig_cumulative = go.Figure()
    fig_cumulative.add_trace(go.Scatter(
        x=df['date'],
        y=df['cumulative_pnl'],
        mode='lines',
        line=dict(color='#2E86AB', width=2),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.1)',
        name='Cumulative P&L',
        yaxis='y'
    ))
    # Add second y-axis for number of trades
    fig_cumulative.add_trace(go.Scatter(
        x=df['date'],
        y=df['cumulative_trades'],
        mode='lines',
        line=dict(color='#A23B72', width=2),
        name='Number of Trades',
        yaxis='y2'
    ))
    fig_cumulative.update_layout(
        xaxis=dict(title=dict(text="Date", font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="Cumulative P&L ($)", font=dict(size=14)), tickfont=dict(size=12)),
        yaxis2=dict(
            title=dict(text="Number of Trades", font=dict(size=14)),
            overlaying='y',
            side='right',
            tickfont=dict(size=12)
        ),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    st.plotly_chart(fig_cumulative, use_container_width=True)

with row1_col2:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Daily P&L</h1>", unsafe_allow_html=True)
    daily_display_type = st.radio(
        "",
        ["Dollar P&L", "Percentage Return"],
        key="daily_display_type",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if daily_display_type == "Dollar P&L":
        y_data = daily['pnl_daily']
        yaxis_title = "Daily P&L ($)"
        marker_colors = ['green' if x > 0 else 'red' for x in daily['pnl_daily']]
        # Calculate S&P 500 dollar P&L assuming $2000 investment
        sp500_initial = 50000
        sp500_y_data = daily['sp500_return_pct'] / 100 * sp500_initial  # Convert % to dollar amount
    else:  # Percentage Return
        y_data = daily['daily_return_pct'] * 100  # Convert to percentage
        yaxis_title = "Daily Return (%)"
        marker_colors = ['green' if x > 0 else 'red' for x in daily['daily_return_pct']]
        # Use S&P 500 percentage return directly
        sp500_y_data = daily['sp500_return_pct']
    
    fig_daily_bar = go.Figure()
    fig_daily_bar.add_trace(go.Bar(
        x=daily.index,
        y=y_data,
        marker_color=marker_colors,
        name='Your Strategy',
        opacity=0.7
    ))
    # Add S&P 500 line overlay
    if 'sp500_return_pct' in daily.columns and daily['sp500_return_pct'].notna().any():
        fig_daily_bar.add_trace(go.Scatter(
            x=daily.index,
            y=sp500_y_data,
            mode='lines',
            line=dict(color='black', width=2),
            name='S&P 500',
            yaxis='y'
        ))
    fig_daily_bar.update_layout(
        xaxis=dict(title=dict(text="Date", font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text=yaxis_title, font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    st.plotly_chart(fig_daily_bar, use_container_width=True)

st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)  # Row spacing

# Second Row: Histograms with dropdown
row2_col1, row2_col2 = st.columns(2, gap="large")

with row2_col1:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Per Trade Returns Distribution</h1>", unsafe_allow_html=True)
    return_type_trade = st.radio(
        "",
        ["Percentage Returns", "Dollar P&L"],
        key="trade_return_type",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if return_type_trade == "Percentage Returns":
        data_trade = df['return_pct_individual'] * 100  # Convert to percentage
        xaxis_title = "Return (%)"
    else:
        data_trade = df['pnl']
        xaxis_title = "P&L ($)"
    
    fig_trade_hist = go.Figure()
    fig_trade_hist.add_trace(go.Histogram(
        x=data_trade,
        nbinsx=120,
        marker=dict(color='#A23B72', line=dict(color='white', width=1)),
        name='Trade Returns'
    ))
    fig_trade_hist.update_layout(
        xaxis=dict(title=dict(text=xaxis_title, font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="Frequency", font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_trade_hist, use_container_width=True)

with row2_col2:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Per Day Returns Distribution</h1>", unsafe_allow_html=True)
    return_type_daily = st.radio(
        "",
        ["Percentage Returns", "Dollar P&L"],
        key="daily_return_type",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if return_type_daily == "Percentage Returns":
        data_daily = daily['daily_return_pct'] * 100  # Convert to percentage
        xaxis_title = "Return (%)"
    else:
        data_daily = daily['pnl_daily']
        xaxis_title = "P&L ($)"
    
    fig_daily_hist = go.Figure()
    fig_daily_hist.add_trace(go.Histogram(
        x=data_daily,
        nbinsx=120,
        marker=dict(color='#A23B72', line=dict(color='white', width=1)),
        name='Daily Returns'
    ))
    fig_daily_hist.update_layout(
        xaxis=dict(title=dict(text=xaxis_title, font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="Frequency", font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_daily_hist, use_container_width=True)

st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)  # Row spacing

# Third Row: Basis vs Return Scatter and Drawdown Curve
row3_col1, row3_col2 = st.columns(2, gap="large")

with row3_col1:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Basis vs Return</h1>", unsafe_allow_html=True)
    scatter_type = st.radio(
        "",
        ["Per Trade", "Per Day"],
        key="scatter_type",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if scatter_type == "Per Trade":
        x_data = df['basis']
        y_data = df['return_pct_individual'] * 100  # Convert to percentage
        xaxis_title = "Basis ($)"
        yaxis_title = "Return (%)"
    else:  # Per Day
        x_data = daily['basis_daily']
        y_data = daily['daily_return_pct'] * 100  # Convert to percentage
        xaxis_title = "Daily Basis ($)"
        yaxis_title = "Daily Return (%)"
    
    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode='markers',
        marker=dict(
            color=y_data,
            colorscale='RdYlGn',
            size=6,
            showscale=True,
            colorbar=dict(title="Return (%)")
        ),
        name='Basis vs Return'
    ))
    fig_scatter.update_layout(
        xaxis=dict(title=dict(text=xaxis_title, font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text=yaxis_title, font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with row3_col2:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Drawdown Curve</h1>", unsafe_allow_html=True)
    st.markdown('<div style="height: 50px;"></div>', unsafe_allow_html=True)  # Spacer to align with selector
    fig_drawdown = go.Figure()
    fig_drawdown.add_trace(go.Scatter(
        x=daily.index,
        y=daily['drawdown'] * 100,  # Convert to percentage
        mode='lines',
        fill='tozeroy',
        fillcolor='rgba(255, 0, 0, 0.3)',
        line=dict(color='red', width=2),
        name='Drawdown'
    ))
    fig_drawdown.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig_drawdown.update_layout(
        xaxis=dict(title=dict(text="Date", font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="Drawdown (%)", font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_drawdown, use_container_width=True)

st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)  # Row spacing


final_row_col1, final_row_col2 = st.columns(2, gap="large")

with final_row_col1:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Bot vs S&P 500 Per-Trade Returns</h1>", unsafe_allow_html=True)
    # Per-trade SP500 comparison
    scatter_mask = df['return_pct'].notna() & df['sp500_return_trade'].notna()
    scatter_df = df.loc[scatter_mask]
    
    fig_scatter_sp500 = go.Figure()
    fig_scatter_sp500.add_trace(go.Scatter(
        x=scatter_df['sp500_return_trade'],
        y=scatter_df['return_pct'],
        mode='markers',
        marker=dict(
            size=6,
            opacity=0.9,
            color='#2E86AB'
        ),
        name='Trade Returns',
        text=scatter_df['symbol'] if 'symbol' in scatter_df.columns else None,
        hovertemplate='<b>%{text}</b><br>SP500: %{x:.2f}%<br>Trade: %{y:.2f}%<extra></extra>'
    ))
    
    # Add reference lines at 0
    fig_scatter_sp500.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig_scatter_sp500.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
    fig_scatter_sp500.update_layout(
        xaxis=dict(title=dict(text="S&P 500 Return (%) [Holding Period]", font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="Trade Return (%)", font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_scatter_sp500, use_container_width=True)

with final_row_col2:
    st.markdown("<h1 style='font-size: 24px; font-weight: bold;'>Rolling Correlation (40-trade window)</h1>", unsafe_allow_html=True)
    
    # Use trade_by_sell_date for rolling correlation
    fig_roll_corr = go.Figure()
    if trade_by_sell_date is not None and not trade_by_sell_date.empty:
        roll_corr_mask = trade_by_sell_date['roll_corr_spx'].notna()
        roll_corr_data = trade_by_sell_date.loc[roll_corr_mask]
        if not roll_corr_data.empty:
            fig_roll_corr.add_trace(go.Scatter(
                x=roll_corr_data.index,
                y=roll_corr_data['roll_corr_spx'],
                mode='lines',
                line=dict(color='#A23B72', width=2),
                name='Rolling Correlation'
            ))
    
    # Add reference line at 0
    fig_roll_corr.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
    fig_roll_corr.update_layout(
        xaxis=dict(title=dict(text="Date", font=dict(size=14)), tickfont=dict(size=12)),
        yaxis=dict(title=dict(text="Rolling Correlation", font=dict(size=14)), tickfont=dict(size=12)),
        height=320,
        margin=dict(l=20, r=20, t=10, b=10),
        font=dict(family="Times New Roman, Times, serif"),
        showlegend=False
    )
    st.plotly_chart(fig_roll_corr, use_container_width=True)

st.markdown("---")

