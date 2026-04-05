"""
main.py — Daily Risk Control Report Generator

Run this script each day before your presentation:
    python main.py

It will:
  1. Fetch latest price data
  2. Calculate portfolio returns and risk metrics
  3. Run all monitoring checks
  4. Print the daily report to terminal
  5. Save a copy to reports/ folder
  6. Print presentation speaking notes
"""

import numpy as np
import pandas as pd

from config import HOLDINGS, LOOKBACK_DAYS
from data_fetcher import fetch_portfolio_prices, get_current_prices
from risk_metrics import daily_returns, calculate_all_metrics
from portfolio_monitor import run_all_checks
from daily_report import format_report, save_report, generate_presentation_notes


def build_portfolio_series(stock_prices: pd.DataFrame) -> pd.Series:
    """
    Build a portfolio value time series from individual stock prices.

    Uses the number of shares from HOLDINGS to weight each stock.
    """
    portfolio_value = pd.Series(0.0, index=stock_prices.index)

    for ticker, shares, _ in HOLDINGS:
        if ticker in stock_prices.columns:
            portfolio_value += stock_prices[ticker] * shares

    return portfolio_value


def main():
    print("📊 Risk Control Toolkit — Generating Daily Report\n")

    # Step 1: Fetch data
    print("[1/4] Fetching price data...")
    stock_prices, benchmark_prices = fetch_portfolio_prices()

    # Step 2: Build portfolio and calculate metrics
    print("[2/4] Calculating risk metrics...")
    portfolio_prices = build_portfolio_series(stock_prices)
    portfolio_returns = daily_returns(portfolio_prices)
    benchmark_returns = daily_returns(benchmark_prices)

    metrics = calculate_all_metrics(
        portfolio_returns,
        portfolio_prices,
        benchmark_returns,
    )

    # Current values
    portfolio_value = portfolio_prices.iloc[-1]
    initial_value = portfolio_prices.iloc[0]
    daily_ret = portfolio_returns.iloc[-1] if len(portfolio_returns) > 0 else 0
    cumulative_ret = (portfolio_value - initial_value) / initial_value

    # Step 3: Run monitoring checks
    print("[3/4] Running risk checks...")
    tickers = [h[0] for h in HOLDINGS]
    current_prices = get_current_prices(tickers)

    alerts, weights, sector_weights = run_all_checks(
        current_prices=current_prices,
        current_drawdown=metrics["max_drawdown"],
        current_vol=metrics["annualized_volatility"],
    )

    # Step 4: Generate report
    print("[4/4] Generating report...\n")
    report = format_report(
        metrics=metrics,
        alerts=alerts,
        weights=weights,
        sector_weights=sector_weights,
        portfolio_value=portfolio_value,
        daily_return=daily_ret,
        cumulative_return=cumulative_ret,
    )

    # Print to terminal
    print(report)

    # Save to file
    filepath = save_report(report)
    print(f"\n📁 Report saved to: {filepath}")

    # Presentation notes
    print("\n")
    notes = generate_presentation_notes(metrics, alerts)
    print(notes)


if __name__ == "__main__":
    main()
