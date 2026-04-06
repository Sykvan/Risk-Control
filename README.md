# 📊 Portfolio Risk Control Dashboard

A free, open-source risk management toolkit for investment clubs and individual investors. Supports multi-market portfolios (US, HK, A-shares) with automatic currency conversion.

**[Live Demo](https://datqm5aprgehrabexknrhl.streamlit.app/)** — try it now, no install needed.

## Features

- **No code needed** — configure your portfolio through the sidebar UI
- **Multi-market support** — US stocks, Hong Kong stocks, A-shares with auto FX conversion
- **Risk metrics** — Volatility, VaR, Sharpe Ratio, Sortino Ratio, Max Drawdown
- **Interactive charts** — Plotly charts with zoom, pan, and range selection
- **Correlation analysis** — Heatmap showing diversification quality
- **Stress testing** — Pre-built and custom scenarios with per-stock breakdown
- **Currency exposure** — Pie chart showing FX risk distribution
- **Automated alerts** — Email notifications via GitHub Actions (optional)
- **Import/Export** — Save and load portfolio configs as JSON

## Quick Start (3 minutes)

### Option A: Deploy your own (recommended)

1. **Fork** this repo (click the Fork button above)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub → Click **New app**
4. Select your forked repo → Set main file to `app.py` → **Deploy**
5. Configure your portfolio in the sidebar — done!

### Option B: Run locally

```bash
git clone https://github.com/sykvan/Risk-Control.git
cd Risk-Control
pip install -r requirements.txt
streamlit run app.py
```

## Ticker Format

| Market | Format | Example |
|--------|--------|---------|
| US stocks | Ticker symbol | `AAPL`, `MSFT`, `GOOGL` |
| HK stocks | Code + `.HK` | `0700.HK`, `9988.HK` |
| A-shares (Shanghai) | Code + `.SS` | `600519.SS` |
| A-shares (Shenzhen) | Code + `.SZ` | `000858.SZ` |
| ETFs | Same as stocks | `SPY`, `QQQ`, `510300.SS` |

## Project Structure

```
Risk-Control/
├── app.py               # Main dashboard (Streamlit)
├── main.py              # CLI report generator
├── config.py            # Config for CLI tool
├── risk_metrics.py      # Core risk calculations
├── data_fetcher.py      # Price data fetching
├── portfolio_monitor.py # Alert system
├── daily_report.py      # Text report generator
├── alert_notifier.py    # Email notification script
├── requirements.txt     # Python dependencies
└── .github/workflows/
    └── daily_alert.yml  # Automated daily checks
```

## Automated Email Alerts (Optional)

Get notified when risk limits are breached:

1. In your GitHub repo: **Settings → Secrets → Actions**
2. Add three secrets:
   - `EMAIL_SENDER` — your Gmail address
   - `EMAIL_PASSWORD` — [Gmail App Password](https://myaccount.google.com/apppasswords)
   - `EMAIL_RECEIVER` — where to receive alerts
3. The workflow runs every weekday at 10pm Beijing time

## Risk Metrics Explained

| Metric | What it means |
|--------|---------------|
| Volatility | Annual price swing magnitude — higher = more risk |
| VaR (95%) | Max expected daily loss with 95% confidence |
| Max Drawdown | Largest peak-to-trough decline in history |
| Sharpe Ratio | Return per unit of risk (>1 good, >2 excellent) |
| Sortino Ratio | Like Sharpe but only penalizes downside |
| Beta | Sensitivity to market moves (1.0 = same as market) |

## Contributing

Pull requests welcome! Some ideas:
- Add more risk metrics (CVaR, Treynor ratio)
- Support more markets (Japan, Europe, crypto)
- Add portfolio optimization suggestions
- Improve mobile UI

## License

MIT — free for personal and commercial use.

## Credits

Built by a finance student for investment clubs everywhere.
Data powered by [Yahoo Finance](https://finance.yahoo.com) via [yfinance](https://github.com/ranaroussi/yfinance).
