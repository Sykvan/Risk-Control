"""
portfolio_monitor.py — Position Monitoring & Alert System

Checks portfolio against risk limits and generates alerts.
"""

import pandas as pd
from config import HOLDINGS, SECTORS, RISK_LIMITS


def calculate_weights(current_prices: dict) -> dict:
    """
    Calculate current portfolio weights based on market value.

    Returns dict with ticker -> weight (0 to 1).
    """
    # Calculate market value of each position
    values = {}
    for ticker, shares, _ in HOLDINGS:
        price = current_prices.get(ticker, 0)
        values[ticker] = shares * price

    total_value = sum(values.values())
    if total_value == 0:
        return {t: 0 for t in values}

    weights = {t: v / total_value for t, v in values.items()}
    return weights


def calculate_sector_weights(stock_weights: dict) -> dict:
    """
    Aggregate stock weights by sector.
    """
    sector_weights = {}
    for ticker, weight in stock_weights.items():
        sector = SECTORS.get(ticker, "Other")
        sector_weights[sector] = sector_weights.get(sector, 0) + weight
    return sector_weights


def check_concentration(stock_weights: dict, sector_weights: dict) -> list[dict]:
    """
    Check if any single stock or sector exceeds weight limits.

    Returns a list of alert dictionaries.
    """
    alerts = []
    max_stock = RISK_LIMITS["max_single_stock_weight"]
    max_sector = RISK_LIMITS["max_sector_weight"]

    # Check individual stock weights
    for ticker, weight in sorted(stock_weights.items(), key=lambda x: -x[1]):
        if weight > max_stock:
            alerts.append({
                "level": "WARN",
                "type": "Stock Concentration",
                "message": (
                    f"{ticker} weight {weight:.1%} exceeds "
                    f"limit {max_stock:.0%}"
                ),
            })

    # Check sector weights
    for sector, weight in sorted(sector_weights.items(), key=lambda x: -x[1]):
        if weight > max_sector:
            alerts.append({
                "level": "WARN",
                "type": "Sector Concentration",
                "message": (
                    f"{sector} sector weight {weight:.1%} exceeds "
                    f"limit {max_sector:.0%}"
                ),
            })

    return alerts


def check_stop_loss(current_prices: dict) -> list[dict]:
    """
    Check if any stock has dropped below the stop-loss threshold
    relative to its cost basis.
    """
    alerts = []
    threshold = RISK_LIMITS["stop_loss_pct"]

    for ticker, shares, cost in HOLDINGS:
        current = current_prices.get(ticker, cost)
        pnl_pct = (current - cost) / cost

        if pnl_pct <= threshold:
            alerts.append({
                "level": "DANGER",
                "type": "Stop Loss",
                "message": (
                    f"{ticker} is down {pnl_pct:.1%} from cost "
                    f"(cost: {cost:.2f}, now: {current:.2f})"
                ),
            })

    return alerts


def check_drawdown(current_drawdown: float) -> list[dict]:
    """
    Check if portfolio-level drawdown exceeds the limit.
    """
    alerts = []
    limit = RISK_LIMITS["max_portfolio_drawdown"]

    if current_drawdown <= limit:
        alerts.append({
            "level": "DANGER",
            "type": "Portfolio Drawdown",
            "message": (
                f"Drawdown {current_drawdown:.1%} exceeds "
                f"limit {limit:.0%}"
            ),
        })

    return alerts


def check_volatility(current_vol: float) -> list[dict]:
    """
    Check if annualized volatility exceeds the limit.
    """
    alerts = []
    limit = RISK_LIMITS["max_volatility"]

    if current_vol > limit:
        alerts.append({
            "level": "WARN",
            "type": "High Volatility",
            "message": (
                f"Annualized volatility {current_vol:.1%} exceeds "
                f"limit {limit:.0%}"
            ),
        })

    return alerts


def run_all_checks(
    current_prices: dict,
    current_drawdown: float,
    current_vol: float,
) -> list[dict]:
    """
    Run all monitoring checks and return combined alerts.
    """
    weights = calculate_weights(current_prices)
    sector_weights = calculate_sector_weights(weights)

    all_alerts = []
    all_alerts.extend(check_concentration(weights, sector_weights))
    all_alerts.extend(check_stop_loss(current_prices))
    all_alerts.extend(check_drawdown(current_drawdown))
    all_alerts.extend(check_volatility(current_vol))

    return all_alerts, weights, sector_weights
