"""
data_fetcher.py — Fetch historical price data using Yahoo Finance

Supports multi-market tickers (US, HK, A-shares).
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import HOLDINGS, BENCHMARK, LOOKBACK_DAYS


def fetch_prices(tickers: list[str], days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """
    Fetch adjusted close prices for a list of tickers.

    Args:
        tickers: List of Yahoo Finance ticker symbols
        days: Number of calendar days to look back

    Returns:
        DataFrame with dates as index and tickers as columns
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    print(f"Fetching data for {len(tickers)} tickers...")
    data = yf.download(
        tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )

    # yfinance returns multi-level columns for multiple tickers
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]
        prices.columns = tickers

    # Drop rows where all values are NaN, forward-fill the rest
    prices = prices.dropna(how="all").ffill()
    return prices


def fetch_portfolio_prices() -> tuple[pd.DataFrame, pd.Series]:
    """
    Fetch prices for all holdings and the benchmark.

    Returns:
        (stock_prices DataFrame, benchmark_prices Series)
    """
    tickers = [h[0] for h in HOLDINGS]
    all_tickers = tickers + [BENCHMARK]

    prices = fetch_prices(all_tickers)

    stock_prices = prices[tickers]
    benchmark_prices = prices[BENCHMARK]

    return stock_prices, benchmark_prices


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """
    Get the most recent closing price for each ticker.

    Returns:
        Dict mapping ticker -> latest price
    """
    prices = fetch_prices(tickers, days=5)
    latest = prices.iloc[-1]
    return latest.to_dict()


if __name__ == "__main__":
    # Quick test
    stock_prices, bench = fetch_portfolio_prices()
    print(f"\nFetched {len(stock_prices)} days of data")
    print(f"Tickers: {list(stock_prices.columns)}")
    print(f"\nLatest prices:\n{stock_prices.iloc[-1]}")
