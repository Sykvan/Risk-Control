"""
risk_metrics.py — Core Risk Metric Calculations

All the key risk indicators used in portfolio risk management.
Each function is self-contained and well-documented for learning.
"""

import numpy as np
import pandas as pd
from config import RISK_FREE_RATE, VAR_CONFIDENCE


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily percentage returns from price data.

    Example: if price goes from 100 to 102, return = 0.02 (2%)
    """
    return prices.pct_change().dropna()


def annualized_volatility(returns: pd.Series) -> float:
    """
    Annualized volatility = daily std dev * sqrt(252).

    252 = typical trading days per year.
    Higher volatility = more risk.

    Good reference:
      < 15%  = Low volatility
      15-25% = Medium
      > 25%  = High volatility
    """
    return returns.std() * np.sqrt(252)


def max_drawdown(prices: pd.Series) -> float:
    """
    Maximum drawdown = largest peak-to-trough decline.

    This measures the worst loss you would have experienced
    if you bought at the peak and sold at the bottom.

    Returns a negative number (e.g., -0.15 means -15%).
    """
    cumulative_max = prices.cummax()
    drawdown = (prices - cumulative_max) / cumulative_max
    return drawdown.min()


def value_at_risk(returns: pd.Series, confidence: float = VAR_CONFIDENCE) -> float:
    """
    Historical Value at Risk (VaR).

    "At 95% confidence, daily loss will not exceed X%."

    Uses the percentile method (simplest approach).
    Returns a negative number (e.g., -0.023 means -2.3% daily VaR).
    """
    return np.percentile(returns, (1 - confidence) * 100)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    """
    Sharpe Ratio = (annualized return - risk free rate) / annualized volatility.

    Measures return per unit of TOTAL risk.

    Good reference:
      < 0    = Losing money relative to risk-free
      0 - 1  = Acceptable
      1 - 2  = Good
      > 2    = Excellent
    """
    annual_return = returns.mean() * 252
    annual_vol = annualized_volatility(returns)
    if annual_vol == 0:
        return 0.0
    return (annual_return - risk_free_rate) / annual_vol


def sortino_ratio(returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    """
    Sortino Ratio = (annualized return - risk free rate) / downside deviation.

    Like Sharpe, but only penalizes DOWNSIDE volatility.
    This is fairer because upside volatility is actually good!
    """
    annual_return = returns.mean() * 252
    downside = returns[returns < 0]
    downside_std = downside.std() * np.sqrt(252) if len(downside) > 0 else 0.0
    if downside_std == 0:
        return 0.0
    return (annual_return - risk_free_rate) / downside_std


def beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Beta = Cov(portfolio, benchmark) / Var(benchmark).

    Measures how sensitive the portfolio is to market movements.
      Beta = 1.0 → moves exactly with market
      Beta > 1.0 → more volatile than market
      Beta < 1.0 → less volatile than market
      Beta < 0   → moves opposite to market (rare)
    """
    # Align the two series by date
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    cov_matrix = aligned.cov()
    covariance = cov_matrix.iloc[0, 1]
    benchmark_var = cov_matrix.iloc[1, 1]
    if benchmark_var == 0:
        return 0.0
    return covariance / benchmark_var


def calculate_all_metrics(
    portfolio_returns: pd.Series,
    portfolio_prices: pd.Series,
    benchmark_returns: pd.Series,
) -> dict:
    """
    Calculate all risk metrics at once. Returns a clean dictionary.
    """
    return {
        "annualized_volatility": annualized_volatility(portfolio_returns),
        "var_95_daily": value_at_risk(portfolio_returns),
        "max_drawdown": max_drawdown(portfolio_prices),
        "sharpe_ratio": sharpe_ratio(portfolio_returns),
        "sortino_ratio": sortino_ratio(portfolio_returns),
        "beta": beta(portfolio_returns, benchmark_returns),
    }
