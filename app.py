"""
app.py — Web Dashboard for Risk Control (Streamlit)

Run locally:   streamlit run app.py
Deploy to web: Push to GitHub, then connect to Streamlit Cloud (free)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Config ---
st.set_page_config(
    page_title="Risk Control Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Portfolio Risk Control Dashboard")
st.caption(f"Last updated: {datetime.today().strftime('%Y-%m-%d %H:%M')}")

# =============================================================
# DATA — Edit these to match your portfolio
# =============================================================

HOLDINGS = [
    ("AAPL",      50,  178.00, "Technology"),
    ("MSFT",      30,  380.00, "Technology"),
    ("NVDA",      20,  720.00, "Technology"),
    ("0700.HK",  100,  320.00, "Technology"),
    ("9988.HK",  200,   80.00, "E-Commerce"),
    ("600519.SS",  5, 1680.00, "Consumer"),
]

RISK_LIMITS = {
    "max_single_stock_weight": 0.20,
    "max_sector_weight":       0.40,
    "stop_loss_pct":           -0.10,
    "max_portfolio_drawdown":  -0.15,
    "max_volatility":          0.30,
}


# =============================================================
# HELPER FUNCTIONS
# =============================================================

@st.cache_data(ttl=300)
def load_prices():
    """
    Fetch price data. Different markets have different trading days,
    so we forward-fill each stock and only keep dates where ALL have data.
    """
    try:
        import yfinance as yf
        tickers = [h[0] for h in HOLDINGS]
        end = datetime.today()
        start = end - timedelta(days=250)
        data = yf.download(
            tickers, start=start, end=end,
            auto_adjust=True, progress=False,
        )
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"]
        else:
            prices = data[["Close"]]
            prices.columns = tickers

        # Forward-fill each stock, then keep only rows where ALL have data
        prices = prices.ffill().dropna()

        if len(prices) < 10:
            raise ValueError("Not enough overlapping data")

        return prices

    except Exception as e:
        st.warning(f"Using demo data ({e})")
        dates = pd.date_range(end=datetime.today(), periods=120, freq="B")
        np.random.seed(42)
        demo = {}
        for ticker, _, cost, _ in HOLDINGS:
            returns = np.random.normal(0.0005, 0.02, len(dates))
            prices = cost * np.cumprod(1 + returns)
            demo[ticker] = prices
        return pd.DataFrame(demo, index=dates)


def calc_risk_metrics(returns):
    """Calculate all risk metrics from a return series."""
    returns = returns.dropna()
    if len(returns) < 2:
        return {
            "Annualized Volatility": 0.0,
            "VaR (95%, 1-day)": 0.0,
            "Sharpe Ratio": 0.0,
            "Sortino Ratio": 0.0,
        }
    vol = returns.std() * np.sqrt(252)
    var_95 = float(np.percentile(returns.values, 5))
    sharpe = (returns.mean() * 252 - 0.04) / vol if vol > 0 else 0.0
    downside = returns[returns < 0]
    down_std = downside.std() * np.sqrt(252) if len(downside) > 1 else 0.0
    sortino = (returns.mean() * 252 - 0.04) / down_std if down_std > 0 else 0.0
    return {
        "Annualized Volatility": vol,
        "VaR (95%, 1-day)": var_95,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
    }


def safe_price(current_prices, ticker, fallback_cost):
    """Get current price, falling back to cost if data is missing."""
    price = current_prices.get(ticker, fallback_cost)
    if pd.isna(price) or price <= 0:
        return fallback_cost
    return float(price)


# =============================================================
# LOAD DATA
# =============================================================

prices = load_prices()

# Build portfolio value series using aligned data
portfolio_value = pd.Series(0.0, index=prices.index)
for ticker, shares, cost, _ in HOLDINGS:
    if ticker in prices.columns:
        portfolio_value += prices[ticker] * shares
    else:
        portfolio_value += cost * shares

portfolio_returns = portfolio_value.pct_change().dropna()

# Current prices and weights (with NaN safety)
raw_current = prices.iloc[-1].to_dict()
current_prices = {}
for ticker, shares, cost, _ in HOLDINGS:
    current_prices[ticker] = safe_price(raw_current, ticker, cost)

total_value = sum(shares * current_prices[t] for t, shares, _, _ in HOLDINGS)
weights = {}
for ticker, shares, _, _ in HOLDINGS:
    weights[ticker] = (shares * current_prices[ticker]) / total_value if total_value > 0 else 0


# =============================================================
# DASHBOARD LAYOUT
# =============================================================

# --- Row 1: Key Numbers ---
col1, col2, col3, col4 = st.columns(4)

daily_ret = portfolio_returns.iloc[-1] if len(portfolio_returns) > 0 else 0.0
cummax = portfolio_value.cummax()
drawdown_series = (portfolio_value - cummax) / cummax
max_drawdown = drawdown_series.min() if len(drawdown_series) > 0 else 0.0

col1.metric("Portfolio Value", f"${total_value:,.0f}")
col2.metric("Daily Return", f"{daily_ret:.2%}")
col3.metric("Max Drawdown", f"{max_drawdown:.2%}")
col4.metric("Positions", f"{len(HOLDINGS)}")


# --- Row 2: Charts ---
st.divider()
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Portfolio Value")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=portfolio_value.index, y=portfolio_value.values,
        mode="lines", line=dict(color="#2B5797", width=2),
        hovertemplate="Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.0f}<extra></extra>",
    ))
    fig1.update_layout(
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(tickprefix="$", tickformat=","),
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(label="All", step="all"),
                ],
                font=dict(size=11),
            ),
            rangeslider=dict(visible=True, thickness=0.08),
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig1, use_container_width=True)

with chart_col2:
    st.subheader("Daily Returns")
    colors = ["#2E7D32" if r >= 0 else "#C62828" for r in portfolio_returns.values]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=portfolio_returns.index, y=portfolio_returns.values,
        marker_color=colors,
        hovertemplate="Date: %{x|%Y-%m-%d}<br>Return: %{y:.2%}<extra></extra>",
    ))
    fig2.update_layout(
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(tickformat=".1%"),
        xaxis=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(label="All", step="all"),
                ],
                font=dict(size=11),
            ),
            rangeslider=dict(visible=True, thickness=0.08),
        ),
        hovermode="x unified",
    )
    st.plotly_chart(fig2, use_container_width=True)


# --- Row 3: Risk Metrics ---
st.divider()
st.subheader("Risk Metrics")

metrics = calc_risk_metrics(portfolio_returns)
mcols = st.columns(len(metrics))
for i, (name, value) in enumerate(metrics.items()):
    if "Ratio" in name:
        mcols[i].metric(name, f"{value:.2f}")
    else:
        mcols[i].metric(name, f"{value:.2%}")


# --- Row 4: Holdings Table & Alerts ---
st.divider()
table_col, alert_col = st.columns([3, 2])

with table_col:
    st.subheader("Current Holdings")
    rows = []
    for ticker, shares, cost, sector in HOLDINGS:
        current = current_prices[ticker]
        pnl_pct = (current - cost) / cost if cost > 0 else 0
        mkt_value = shares * current
        rows.append({
            "Ticker": ticker,
            "Sector": sector,
            "Shares": shares,
            "Cost": f"${cost:.2f}",
            "Current": f"${current:.2f}",
            "P&L": f"{pnl_pct:+.1%}",
            "Weight": f"{weights.get(ticker, 0):.1%}",
            "Value": f"${mkt_value:,.0f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with alert_col:
    st.subheader("Alerts")
    alert_count = 0

    for ticker, w in weights.items():
        if w > RISK_LIMITS["max_single_stock_weight"]:
            st.error(f"⚠️ {ticker} weight {w:.1%} exceeds {RISK_LIMITS['max_single_stock_weight']:.0%} limit")
            alert_count += 1

    sector_w = {}
    for ticker, _, _, sector in HOLDINGS:
        sector_w[sector] = sector_w.get(sector, 0) + weights.get(ticker, 0)
    for sector, w in sector_w.items():
        if w > RISK_LIMITS["max_sector_weight"]:
            st.error(f"⚠️ {sector} sector {w:.1%} exceeds {RISK_LIMITS['max_sector_weight']:.0%} limit")
            alert_count += 1

    for ticker, shares, cost, _ in HOLDINGS:
        current = current_prices[ticker]
        pnl = (current - cost) / cost if cost > 0 else 0
        if pnl <= RISK_LIMITS["stop_loss_pct"]:
            st.error(f"🔴 {ticker} down {pnl:.1%} — stop loss triggered!")
            alert_count += 1

    if max_drawdown <= RISK_LIMITS["max_portfolio_drawdown"]:
        st.error(f"🔴 Drawdown {max_drawdown:.1%} exceeds {RISK_LIMITS['max_portfolio_drawdown']:.0%} limit")
        alert_count += 1

    vol = metrics["Annualized Volatility"]
    if vol > RISK_LIMITS["max_volatility"]:
        st.warning(f"⚠️ Volatility {vol:.1%} exceeds {RISK_LIMITS['max_volatility']:.0%} limit")
        alert_count += 1

    if alert_count == 0:
        st.success("✅ All clear — no risk alerts")


# --- Data Info ---
st.divider()
with st.expander("Data Info"):
    st.write(f"**Data range**: {prices.index[0].strftime('%Y-%m-%d')} to {prices.index[-1].strftime('%Y-%m-%d')}")
    st.write(f"**Trading days**: {len(prices)}")
    st.write(f"**Tickers found**: {', '.join(prices.columns.tolist())}")
    missing = [h[0] for h in HOLDINGS if h[0] not in prices.columns]
    if missing:
        st.warning(f"**Missing tickers** (using cost as price): {', '.join(missing)}")

st.caption("Built with Streamlit • Risk Control Toolkit for Student Investment Club")
