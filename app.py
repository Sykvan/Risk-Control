"""
app.py — Web Dashboard for Risk Control (Streamlit)

Run locally:   streamlit run app.py
Deploy to web: Push to GitHub, then connect to Streamlit Cloud (free)

Anyone with the link can view your risk dashboard!
"""

import streamlit as st
import pandas as pd
import numpy as np
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
    ("AAPL",    50,  178.00, "Technology"),
    ("MSFT",    30,  380.00, "Technology"),
    ("NVDA",    20,  720.00, "Technology"),
    ("0700.HK", 100, 320.00, "Technology"),
    ("9988.HK", 200,  80.00, "E-Commerce"),
    ("600519.SS", 5, 1680.00, "Consumer"),
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

@st.cache_data(ttl=300)  # Cache data for 5 minutes
def load_prices():
    """Fetch price data. Uses yfinance if available, otherwise demo data."""
    try:
        import yfinance as yf
        tickers = [h[0] for h in HOLDINGS]
        end = datetime.today()
        start = end - timedelta(days=180)
        data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            return data["Close"].ffill()
        return data[["Close"]].ffill()
    except Exception:
        # Generate demo data if yfinance fails
        st.warning("Using demo data (install yfinance for live data)")
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
    sharpe = (returns.mean() * 252 - 0.04) / vol if vol > 0 else 0
    downside = returns[returns < 0]
    sortino = (returns.mean() * 252 - 0.04) / (downside.std() * np.sqrt(252)) if len(downside) > 0 else 0
    return {
        "Annualized Volatility": vol,
        "VaR (95%, 1-day)": var_95,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
    }


# =============================================================
# LOAD DATA
# =============================================================

prices = load_prices()

# Build portfolio value series
portfolio_value = pd.Series(0.0, index=prices.index)
for ticker, shares, _, _ in HOLDINGS:
    if ticker in prices.columns:
        portfolio_value += prices[ticker].fillna(0) * shares

portfolio_value = portfolio_value[portfolio_value > 0]
portfolio_returns = portfolio_value.pct_change().dropna()

# Current prices and weights
current_prices = prices.iloc[-1].to_dict()
total_value = sum(shares * current_prices.get(t, cost) for t, shares, cost, _ in HOLDINGS)
weights = {t: (shares * current_prices.get(t, cost)) / total_value for t, shares, cost, _ in HOLDINGS}


# =============================================================
# DASHBOARD LAYOUT
# =============================================================

# --- Row 1: Key Numbers ---
col1, col2, col3, col4 = st.columns(4)

daily_ret = portfolio_returns.iloc[-1] if len(portfolio_returns) > 0 else 0
cummax = portfolio_value.cummax()
drawdown = ((portfolio_value - cummax) / cummax).min()

col1.metric("Portfolio Value", f"${total_value:,.0f}")
col2.metric("Daily Return", f"{daily_ret:.2%}")
col3.metric("Max Drawdown", f"{drawdown:.2%}")
col4.metric("Positions", f"{len(HOLDINGS)}")


# --- Row 2: Charts ---
st.divider()
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Portfolio Value")
    st.line_chart(portfolio_value)

with chart_col2:
    st.subheader("Daily Returns")
    st.bar_chart(portfolio_returns.tail(30))


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
        current = current_prices.get(ticker, cost)
        pnl_pct = (current - cost) / cost
        rows.append({
            "Ticker": ticker,
            "Sector": sector,
            "Shares": shares,
            "Cost": f"${cost:.2f}",
            "Current": f"${current:.2f}",
            "P&L": f"{pnl_pct:.1%}",
            "Weight": f"{weights.get(ticker, 0):.1%}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with alert_col:
    st.subheader("Alerts")
    alert_count = 0

    # Check stock concentration
    for ticker, w in weights.items():
        if w > RISK_LIMITS["max_single_stock_weight"]:
            st.error(f"⚠️ {ticker} weight {w:.1%} > {RISK_LIMITS['max_single_stock_weight']:.0%} limit")
            alert_count += 1

    # Check sector concentration
    sector_w = {}
    for ticker, _, _, sector in HOLDINGS:
        sector_w[sector] = sector_w.get(sector, 0) + weights.get(ticker, 0)
    for sector, w in sector_w.items():
        if w > RISK_LIMITS["max_sector_weight"]:
            st.error(f"⚠️ {sector} sector {w:.1%} > {RISK_LIMITS['max_sector_weight']:.0%} limit")
            alert_count += 1

    # Check stop loss
    for ticker, shares, cost, _ in HOLDINGS:
        current = current_prices.get(ticker, cost)
        pnl = (current - cost) / cost
        if pnl <= RISK_LIMITS["stop_loss_pct"]:
            st.error(f"🔴 {ticker} down {pnl:.1%} — stop loss triggered!")
            alert_count += 1

    # Check drawdown
    if drawdown <= RISK_LIMITS["max_portfolio_drawdown"]:
        st.error(f"🔴 Drawdown {drawdown:.1%} exceeds {RISK_LIMITS['max_portfolio_drawdown']:.0%} limit")
        alert_count += 1

    if alert_count == 0:
        st.success("✅ All clear — no risk alerts")


# --- Footer ---
st.divider()
st.caption("Built with Streamlit • Risk Control Toolkit for Student Investment Club")
