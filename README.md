# 📊 Portfolio Risk Control Toolkit

A beginner-friendly risk control analysis toolkit for student investment clubs.
Supports multi-market portfolios (US, HK, A-shares, etc.).

## Features

- **Risk Metrics** — Volatility, VaR, Max Drawdown, Sharpe Ratio, Beta, Sortino Ratio
- **Daily Risk Report** — Auto-generated markdown report for your 10-min presentation
- **Position Monitoring** — Concentration checks, stop-loss alerts, drawdown warnings

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/risk-control.git
cd risk-control

# 2. Install dependencies
pip install -r requirements.txt

# 3. Edit your portfolio in config.py

# 4. Run the daily report
python main.py
```

## Project Structure

```
risk-control/
├── config.py            # Portfolio holdings & risk thresholds
├── data_fetcher.py      # Fetch price data via yfinance
├── risk_metrics.py      # Core risk calculations
├── portfolio_monitor.py # Position monitoring & alerts
├── daily_report.py      # Generate daily risk report
├── main.py              # Entry point
├── reports/             # Generated reports folder
└── requirements.txt
```

## Configuration

Edit `config.py` to match your club's portfolio:

- **HOLDINGS** — ticker symbol, number of shares, cost basis per share
- **BENCHMARK** — market index for Beta calculation (e.g. SPY, ^HSI, 000300.SS)
- **RISK_LIMITS** — max single-stock weight, stop-loss %, max drawdown %

## Risk Metrics Explained

| Metric | What It Means |
|--------|---------------|
| Volatility | How much the portfolio swings (annualized) |
| VaR (95%) | Max expected daily loss, 95% confidence |
| Max Drawdown | Largest peak-to-trough decline |
| Sharpe Ratio | Return per unit of total risk |
| Beta | Sensitivity to market moves (1.0 = same as market) |
| Sortino Ratio | Return per unit of downside risk |

## License

MIT
