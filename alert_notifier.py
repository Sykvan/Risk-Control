"""
alert_notifier.py — Automated Risk Alert Email Notification

This script is designed to run daily via GitHub Actions.
It checks all risk limits and sends an email if any alerts are triggered.

Setup:
  1. In your GitHub repo, go to Settings → Secrets → Actions
  2. Add these secrets:
     - EMAIL_SENDER:   your Gmail address (e.g. zhangsan@gmail.com)
     - EMAIL_PASSWORD:  Gmail app password (NOT your regular password)
     - EMAIL_RECEIVER:  where to receive alerts (can be same as sender)

  To get a Gmail App Password:
    - Go to myaccount.google.com → Security → 2-Step Verification → App passwords
    - Generate a new app password for "Mail"

  3. The GitHub Actions workflow (.github/workflows/daily_alert.yml) will
     run this script every weekday at a scheduled time.
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd
import numpy as np


# =============================================================
# PORTFOLIO CONFIG (keep in sync with app.py)
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
# DATA
# =============================================================

def fetch_data():
    """Fetch price data and calculate portfolio metrics."""
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

    prices = prices.ffill().dropna()
    return prices


def analyze(prices):
    """Run all risk checks. Returns (alerts, summary)."""
    alerts = []
    tickers = [h[0] for h in HOLDINGS]

    # Current prices
    current_prices = {}
    raw = prices.iloc[-1].to_dict()
    for ticker, shares, cost, _ in HOLDINGS:
        p = raw.get(ticker, cost)
        current_prices[ticker] = cost if (pd.isna(p) or p <= 0) else float(p)

    # Portfolio value & weights
    total_value = sum(s * current_prices[t] for t, s, _, _ in HOLDINGS)
    weights = {t: (s * current_prices[t]) / total_value for t, s, _, _ in HOLDINGS}

    # Portfolio returns
    portfolio_value = pd.Series(0.0, index=prices.index)
    for ticker, shares, cost, _ in HOLDINGS:
        if ticker in prices.columns:
            portfolio_value += prices[ticker] * shares
        else:
            portfolio_value += cost * shares

    portfolio_returns = portfolio_value.pct_change().dropna()
    daily_ret = portfolio_returns.iloc[-1] if len(portfolio_returns) > 0 else 0

    # Risk metrics
    vol = portfolio_returns.std() * np.sqrt(252)
    cummax = portfolio_value.cummax()
    max_dd = ((portfolio_value - cummax) / cummax).min()
    var_95 = float(np.percentile(portfolio_returns.values, 5)) if len(portfolio_returns) > 1 else 0
    sharpe = (portfolio_returns.mean() * 252 - 0.04) / vol if vol > 0 else 0

    # --- Run checks ---

    # Stock concentration
    for ticker, w in weights.items():
        if w > RISK_LIMITS["max_single_stock_weight"]:
            alerts.append(f"WARN: {ticker} weight {w:.1%} exceeds {RISK_LIMITS['max_single_stock_weight']:.0%} limit")

    # Sector concentration
    sector_w = {}
    for ticker, _, _, sector in HOLDINGS:
        sector_w[sector] = sector_w.get(sector, 0) + weights.get(ticker, 0)
    for sector, w in sector_w.items():
        if w > RISK_LIMITS["max_sector_weight"]:
            alerts.append(f"WARN: {sector} sector {w:.1%} exceeds {RISK_LIMITS['max_sector_weight']:.0%} limit")

    # Stop loss
    for ticker, shares, cost, _ in HOLDINGS:
        cur = current_prices[ticker]
        pnl = (cur - cost) / cost if cost > 0 else 0
        if pnl <= RISK_LIMITS["stop_loss_pct"]:
            alerts.append(f"DANGER: {ticker} down {pnl:.1%} from cost (${cost:.2f} -> ${cur:.2f})")

    # Drawdown
    if max_dd <= RISK_LIMITS["max_portfolio_drawdown"]:
        alerts.append(f"DANGER: Portfolio drawdown {max_dd:.1%} exceeds {RISK_LIMITS['max_portfolio_drawdown']:.0%} limit")

    # Volatility
    if vol > RISK_LIMITS["max_volatility"]:
        alerts.append(f"WARN: Volatility {vol:.1%} exceeds {RISK_LIMITS['max_volatility']:.0%} limit")

    # Build summary
    summary = {
        "date": prices.index[-1].strftime("%Y-%m-%d"),
        "total_value": total_value,
        "daily_return": daily_ret,
        "volatility": vol,
        "var_95": var_95,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
    }

    return alerts, summary


# =============================================================
# EMAIL
# =============================================================

def build_email(alerts, summary):
    """Build the email content."""
    date = summary["date"]
    subject = f"[Risk Alert] {len(alerts)} alert(s) triggered — {date}"

    body = f"""Portfolio Risk Alert Report — {date}
{'=' * 50}

PORTFOLIO SUMMARY
  Total Value:     ${summary['total_value']:,.0f}
  Daily Return:    {summary['daily_return']:.2%}
  Volatility:      {summary['volatility']:.1%}
  VaR (95%):       {summary['var_95']:.2%}
  Max Drawdown:    {summary['max_drawdown']:.1%}
  Sharpe Ratio:    {summary['sharpe']:.2f}

ALERTS ({len(alerts)})
{'-' * 50}
"""

    for i, alert in enumerate(alerts, 1):
        body += f"  {i}. {alert}\n"

    body += f"""
{'=' * 50}
View full dashboard: [Your Streamlit URL]
This is an automated alert from your Risk Control Toolkit.
"""
    return subject, body


def send_email(subject, body):
    """Send the alert email via Gmail SMTP."""
    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    receiver = os.environ.get("EMAIL_RECEIVER")

    if not all([sender, password, receiver]):
        print("Email credentials not set. Printing alert to console instead:")
        print(f"\nSubject: {subject}\n")
        print(body)
        return False

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print(f"Alert email sent to {receiver}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


# =============================================================
# MAIN
# =============================================================

def main():
    print(f"Running risk check at {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    prices = fetch_data()
    alerts, summary = analyze(prices)

    print(f"Date: {summary['date']}")
    print(f"Portfolio: ${summary['total_value']:,.0f}")
    print(f"Alerts: {len(alerts)}")

    if alerts:
        subject, body = build_email(alerts, summary)
        send_email(subject, body)
    else:
        print("All clear — no alerts triggered. No email sent.")


if __name__ == "__main__":
    main()
