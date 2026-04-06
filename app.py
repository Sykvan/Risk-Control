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


def get_currency(ticker):
    """Detect currency from ticker suffix."""
    if ticker.endswith(".HK"):
        return "HKD"
    elif ticker.endswith(".SS") or ticker.endswith(".SZ"):
        return "CNY"
    return "USD"


@st.cache_data(ttl=300)
def load_fx_rates():
    """
    Fetch exchange rates: how many USD per 1 unit of foreign currency.
    Returns dict like {"HKD": 0.128, "CNY": 0.137, "USD": 1.0}
    """
    try:
        import yfinance as yf
        end = datetime.today()
        start = end - timedelta(days=250)

        # Fetch HKD->USD and CNY->USD conversion series
        fx_tickers = ["HKDUSD=X", "CNYUSD=X"]
        fx_data = yf.download(fx_tickers, start=start, end=end, progress=False)

        if isinstance(fx_data.columns, pd.MultiIndex):
            fx_close = fx_data["Close"]
        else:
            fx_close = fx_data[["Close"]]

        fx_close = fx_close.ffill().dropna()

        # Latest rates
        hkd_to_usd = float(fx_close["HKDUSD=X"].iloc[-1]) if "HKDUSD=X" in fx_close.columns else 0.128
        cny_to_usd = float(fx_close["CNYUSD=X"].iloc[-1]) if "CNYUSD=X" in fx_close.columns else 0.137

        # Also return full time series for historical conversion
        return {
            "rates": {"USD": 1.0, "HKD": hkd_to_usd, "CNY": cny_to_usd},
            "series": fx_close,
        }
    except Exception:
        return {
            "rates": {"USD": 1.0, "HKD": 0.128, "CNY": 0.137},
            "series": None,
        }


# =============================================================
# LOAD DATA
# =============================================================

prices = load_prices()
fx_data = load_fx_rates()
fx_rates = fx_data["rates"]

# Build portfolio value series — convert all to USD
portfolio_value = pd.Series(0.0, index=prices.index)
for ticker, shares, cost, _ in HOLDINGS:
    ccy = get_currency(ticker)
    rate = fx_rates.get(ccy, 1.0)
    if ticker in prices.columns:
        portfolio_value += prices[ticker] * shares * rate
    else:
        portfolio_value += cost * shares * rate

portfolio_returns = portfolio_value.pct_change().dropna()

# Current prices in local currency and in USD (with NaN safety)
raw_current = prices.iloc[-1].to_dict()
current_prices_local = {}
current_prices_usd = {}
for ticker, shares, cost, _ in HOLDINGS:
    local_price = safe_price(raw_current, ticker, cost)
    ccy = get_currency(ticker)
    rate = fx_rates.get(ccy, 1.0)
    current_prices_local[ticker] = local_price
    current_prices_usd[ticker] = local_price * rate

total_value = sum(shares * current_prices_usd[t] for t, shares, _, _ in HOLDINGS)
weights = {}
for ticker, shares, _, _ in HOLDINGS:
    weights[ticker] = (shares * current_prices_usd[ticker]) / total_value if total_value > 0 else 0


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
    ccy_symbols = {"USD": "$", "HKD": "HK$", "CNY": "¥"}
    rows = []
    for ticker, shares, cost, sector in HOLDINGS:
        ccy = get_currency(ticker)
        sym = ccy_symbols.get(ccy, "$")
        local_price = current_prices_local[ticker]
        usd_value = shares * current_prices_usd[ticker]
        pnl_pct = (local_price - cost) / cost if cost > 0 else 0
        rows.append({
            "Ticker": ticker,
            "Sector": sector,
            "CCY": ccy,
            "Shares": shares,
            "Cost": f"{sym}{cost:.2f}",
            "Current": f"{sym}{local_price:.2f}",
            "P&L": f"{pnl_pct:+.1%}",
            "Weight": f"{weights.get(ticker, 0):.1%}",
            "Value (USD)": f"${usd_value:,.0f}",
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
        current = current_prices_local[ticker]
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


# --- Row 5: Correlation Matrix ---
st.divider()
st.subheader("Correlation Analysis")
st.caption("High correlation between stocks = less diversification. Look for red clusters.")

stock_returns = prices.pct_change().dropna()
corr_matrix = stock_returns.corr()

tickers_list = corr_matrix.columns.tolist()
fig_corr = go.Figure(data=go.Heatmap(
    z=corr_matrix.values,
    x=tickers_list,
    y=tickers_list,
    colorscale=[
        [0, "#2166AC"],
        [0.25, "#67A9CF"],
        [0.5, "#F7F7F7"],
        [0.75, "#EF8A62"],
        [1, "#B2182B"],
    ],
    zmin=-1, zmax=1,
    text=corr_matrix.values.round(2),
    texttemplate="%{text}",
    textfont=dict(size=13),
    hovertemplate="<b>%{x}</b> vs <b>%{y}</b><br>Correlation: %{z:.2f}<extra></extra>",
    colorbar=dict(title="Corr", thickness=12, len=0.6),
))
fig_corr.update_layout(
    height=380, margin=dict(l=0, r=0, t=10, b=0),
    xaxis=dict(side="bottom"),
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(fig_corr, use_container_width=True)

# Identify the most and least correlated pairs
pairs = []
for i in range(len(tickers_list)):
    for j in range(i + 1, len(tickers_list)):
        pairs.append((tickers_list[i], tickers_list[j], corr_matrix.iloc[i, j]))

if pairs:
    pairs.sort(key=lambda x: x[2])
    lowest = pairs[0]
    highest = pairs[-1]
    corr_col1, corr_col2 = st.columns(2)
    corr_col1.metric(
        f"Most correlated: {highest[0]} & {highest[1]}",
        f"{highest[2]:.2f}",
        help="These two stocks move together. Holding both gives less diversification."
    )
    corr_col2.metric(
        f"Least correlated: {lowest[0]} & {lowest[1]}",
        f"{lowest[2]:.2f}",
        help="These two stocks move independently. Good for diversification."
    )


# --- Row 6: Stress Testing ---
st.divider()
st.subheader("Stress Testing")
st.caption("Simulate how the portfolio would react under different market scenarios.")

# Calculate beta for each stock
stock_betas = {}
benchmark_tickers = [h[0] for h in HOLDINGS]
if "SPY" in prices.columns or len(prices.columns) > 0:
    try:
        import yfinance as yf
        spy_data = yf.download("SPY", start=prices.index[0], end=prices.index[-1], auto_adjust=True, progress=False)
        if isinstance(spy_data.columns, pd.MultiIndex):
            spy_prices = spy_data["Close"].squeeze()
        else:
            spy_prices = spy_data["Close"]
        spy_returns = spy_prices.pct_change().dropna()

        for ticker in benchmark_tickers:
            if ticker in stock_returns.columns:
                aligned = pd.concat([stock_returns[ticker], spy_returns], axis=1).dropna()
                if len(aligned) > 10:
                    aligned.columns = ["stock", "spy"]
                    cov = aligned.cov().iloc[0, 1]
                    var_spy = aligned["spy"].var()
                    stock_betas[ticker] = cov / var_spy if var_spy > 0 else 1.0
                else:
                    stock_betas[ticker] = 1.0
            else:
                stock_betas[ticker] = 1.0
    except Exception:
        stock_betas = {h[0]: 1.0 for h in HOLDINGS}
else:
    stock_betas = {h[0]: 1.0 for h in HOLDINGS}

# Scenario definitions
scenarios = {
    "Market drops 10%": -0.10,
    "Market drops 20% (bear market)": -0.20,
    "Market drops 30% (crash)": -0.30,
    "Market rises 10%": 0.10,
    "Market rises 20%": 0.20,
}

# Build stress test results
stress_rows = []
for scenario_name, market_shock in scenarios.items():
    scenario_loss = 0
    details = []
    for ticker, shares, cost, sector in HOLDINGS:
        beta = stock_betas.get(ticker, 1.0)
        stock_move = market_shock * beta
        cur_price = current_prices_usd[ticker]
        position_value = shares * cur_price
        position_loss = position_value * stock_move
        scenario_loss += position_loss
        details.append(f"{ticker}: {stock_move:+.1%}")

    pct_loss = scenario_loss / total_value if total_value > 0 else 0
    stress_rows.append({
        "Scenario": scenario_name,
        "Market move": f"{market_shock:+.0%}",
        "Portfolio impact": f"{pct_loss:+.1%}",
        "Dollar impact": f"${scenario_loss:+,.0f}",
    })

st.dataframe(pd.DataFrame(stress_rows), use_container_width=True, hide_index=True)

# Interactive custom scenario
st.markdown("**Custom scenario**")
custom_col1, custom_col2 = st.columns([1, 2])
with custom_col1:
    custom_shock = st.slider(
        "Market change %", min_value=-50, max_value=50, value=-15, step=1,
        format="%d%%"
    )

custom_loss = 0
custom_detail_rows = []
for ticker, shares, cost, sector in HOLDINGS:
    beta = stock_betas.get(ticker, 1.0)
    stock_move = (custom_shock / 100) * beta
    cur_price = current_prices_usd[ticker]
    position_value = shares * cur_price
    position_loss = position_value * stock_move
    custom_loss += position_loss
    custom_detail_rows.append({
        "Ticker": ticker,
        "Beta": f"{beta:.2f}",
        "Stock impact": f"{stock_move:+.1%}",
        "Position value": f"${position_value:,.0f}",
        "P&L": f"${position_loss:+,.0f}",
    })

custom_pct = custom_loss / total_value if total_value > 0 else 0

with custom_col2:
    c1, c2 = st.columns(2)
    c1.metric("Portfolio impact", f"{custom_pct:+.1%}")
    c2.metric("Dollar impact", f"${custom_loss:+,.0f}")

with st.expander("See per-stock breakdown"):
    st.dataframe(pd.DataFrame(custom_detail_rows), use_container_width=True, hide_index=True)


# --- Row 7: Currency Exposure ---
st.divider()
st.subheader("Currency Exposure")
st.caption("All values are converted to USD using live exchange rates.")

# Calculate exposure by currency
ccy_exposure = {}
for ticker, shares, _, _ in HOLDINGS:
    ccy = get_currency(ticker)
    usd_val = shares * current_prices_usd[ticker]
    ccy_exposure[ccy] = ccy_exposure.get(ccy, 0) + usd_val

ccy_col1, ccy_col2 = st.columns([1, 2])

with ccy_col1:
    # Exchange rate display
    st.markdown("**Current exchange rates**")
    rate_rows = []
    for ccy, rate in fx_rates.items():
        if ccy != "USD":
            rate_rows.append({
                "Pair": f"{ccy}/USD",
                "Rate": f"{rate:.4f}",
                "Meaning": f"1 {ccy} = {rate:.4f} USD",
            })
    if rate_rows:
        st.dataframe(pd.DataFrame(rate_rows), use_container_width=True, hide_index=True)

with ccy_col2:
    # Currency exposure pie chart
    ccy_labels = list(ccy_exposure.keys())
    ccy_values = list(ccy_exposure.values())
    ccy_colors = {"USD": "#2B5797", "HKD": "#D85A30", "CNY": "#C62828"}

    fig_ccy = go.Figure(data=[go.Pie(
        labels=ccy_labels,
        values=ccy_values,
        hole=0.45,
        marker=dict(colors=[ccy_colors.get(c, "#888") for c in ccy_labels]),
        textinfo="label+percent",
        textfont=dict(size=14),
        hovertemplate="<b>%{label}</b><br>Value: $%{value:,.0f}<br>Share: %{percent}<extra></extra>",
    )])
    fig_ccy.update_layout(
        height=280, margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        annotations=[dict(text="FX<br>exposure", x=0.5, y=0.5, font_size=14, showarrow=False,
                          font=dict(color="gray"))],
    )
    st.plotly_chart(fig_ccy, use_container_width=True)

# Risk note
usd_pct = ccy_exposure.get("USD", 0) / total_value * 100 if total_value > 0 else 0
non_usd_pct = 100 - usd_pct
if non_usd_pct > 30:
    st.warning(
        f"⚠️ {non_usd_pct:.0f}% of the portfolio is in non-USD currencies. "
        f"A 5% move in USD/CNY would impact ~{non_usd_pct * 0.05:.1f}% of total portfolio value."
    )
else:
    st.info(
        f"Currency exposure is manageable: {non_usd_pct:.0f}% in non-USD. "
        f"Note: HKD is pegged to USD (low risk), CNY exposure is the main FX risk."
    )


# --- Data Info ---
st.divider()
with st.expander("Data Info"):
    st.write(f"**Data range**: {prices.index[0].strftime('%Y-%m-%d')} to {prices.index[-1].strftime('%Y-%m-%d')}")
    st.write(f"**Trading days**: {len(prices)}")
    st.write(f"**Tickers found**: {', '.join(prices.columns.tolist())}")
    st.write(f"**Exchange rates**: 1 HKD = {fx_rates.get('HKD', 0.128):.4f} USD, 1 CNY = {fx_rates.get('CNY', 0.137):.4f} USD")
    missing = [h[0] for h in HOLDINGS if h[0] not in prices.columns]
    if missing:
        st.warning(f"**Missing tickers** (using cost as price): {', '.join(missing)}")

st.caption("Built with Streamlit • Risk Control Toolkit for Student Investment Club")
