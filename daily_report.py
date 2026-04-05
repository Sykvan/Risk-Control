"""
daily_report.py — Generate Daily Risk Report

Creates a formatted text report for your 10-minute presentation.
Also saves a markdown version to the reports/ folder.
"""

import os
from datetime import datetime
from config import HOLDINGS, BENCHMARK


def format_report(
    metrics: dict,
    alerts: list[dict],
    weights: dict,
    sector_weights: dict,
    portfolio_value: float,
    daily_return: float,
    cumulative_return: float,
) -> str:
    """
    Generate a formatted daily risk report string.
    """
    date_str = datetime.today().strftime("%Y-%m-%d")
    separator = "=" * 60

    lines = []
    lines.append(separator)
    lines.append(f"        DAILY RISK REPORT — {date_str}")
    lines.append(separator)

    # --- Portfolio Summary ---
    lines.append("")
    lines.append("PORTFOLIO SUMMARY")
    lines.append(f"  Total Value:       ${portfolio_value:>12,.2f}")
    lines.append(f"  Daily Return:      {daily_return:>12.2%}")
    lines.append(f"  Cumulative Return: {cumulative_return:>12.2%}")
    lines.append(f"  Benchmark:         {BENCHMARK}")

    # --- Risk Metrics ---
    lines.append("")
    lines.append("RISK METRICS")
    lines.append(f"  Annualized Vol:    {metrics['annualized_volatility']:>12.2%}")
    lines.append(f"  VaR (95%, 1-day):  {metrics['var_95_daily']:>12.2%}")
    lines.append(f"  Max Drawdown:      {metrics['max_drawdown']:>12.2%}")
    lines.append(f"  Sharpe Ratio:      {metrics['sharpe_ratio']:>12.2f}")
    lines.append(f"  Sortino Ratio:     {metrics['sortino_ratio']:>12.2f}")
    lines.append(f"  Beta:              {metrics['beta']:>12.2f}")

    # --- Top Holdings ---
    lines.append("")
    lines.append("TOP HOLDINGS BY WEIGHT")
    sorted_weights = sorted(weights.items(), key=lambda x: -x[1])
    for ticker, w in sorted_weights[:5]:
        bar = "█" * int(w * 40)
        lines.append(f"  {ticker:<12} {w:>6.1%}  {bar}")

    # --- Sector Allocation ---
    lines.append("")
    lines.append("SECTOR ALLOCATION")
    for sector, w in sorted(sector_weights.items(), key=lambda x: -x[1]):
        bar = "█" * int(w * 40)
        lines.append(f"  {sector:<16} {w:>6.1%}  {bar}")

    # --- P&L by Position ---
    lines.append("")
    lines.append("POSITION P&L (vs cost basis)")
    for ticker, shares, cost in HOLDINGS:
        current = weights.get(ticker, 0)  # just show weight for now
        lines.append(f"  {ticker:<12} {shares:>6} shares @ {cost:>8.2f}")

    # --- Alerts ---
    lines.append("")
    if alerts:
        lines.append("⚠️  ALERTS")
        for alert in alerts:
            icon = "🔴" if alert["level"] == "DANGER" else "🟡"
            lines.append(f"  {icon} [{alert['level']}] {alert['message']}")
    else:
        lines.append("✅ ALL CLEAR — No risk alerts triggered.")

    lines.append("")
    lines.append(separator)
    return "\n".join(lines)


def save_report(report_text: str) -> str:
    """
    Save the report as a markdown file in the reports/ folder.
    Returns the file path.
    """
    os.makedirs("reports", exist_ok=True)
    date_str = datetime.today().strftime("%Y-%m-%d")
    filepath = f"reports/risk_report_{date_str}.md"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("```\n")
        f.write(report_text)
        f.write("\n```\n")

    return filepath


def generate_presentation_notes(metrics: dict, alerts: list[dict]) -> str:
    """
    Generate brief speaking notes for your 10-min presentation.

    Structure:
      - 3 min: Portfolio status
      - 4 min: Key risk focus
      - 3 min: Recommendations
    """
    lines = []
    lines.append("PRESENTATION NOTES (10 min)")
    lines.append("-" * 40)

    # Part 1: Status
    lines.append("")
    lines.append("[0:00 - 3:00] PORTFOLIO STATUS")
    lines.append("  • Show portfolio value and daily return")
    lines.append("  • Highlight top/bottom performers today")
    lines.append("  • Quick sector allocation overview")

    # Part 2: Risk Focus
    lines.append("")
    lines.append("[3:00 - 7:00] RISK FOCUS")
    if metrics["annualized_volatility"] > 0.25:
        lines.append("  • Volatility is HIGH — discuss why and potential hedges")
    if metrics["max_drawdown"] < -0.10:
        lines.append("  • Drawdown is significant — review recovery timeline")
    if metrics["beta"] > 1.2:
        lines.append("  • Beta > 1.2 — portfolio amplifies market moves")
    if metrics["sharpe_ratio"] < 0.5:
        lines.append("  • Low Sharpe — risk is not being well compensated")
    if not alerts:
        lines.append("  • No alerts — review why current setup is working")

    # Part 3: Recommendations
    lines.append("")
    lines.append("[7:00 - 10:00] RECOMMENDATIONS")
    if alerts:
        lines.append("  • Address each alert with specific action items")
        for alert in alerts:
            lines.append(f"    → {alert['type']}: {alert['message']}")
    else:
        lines.append("  • Portfolio is within all limits")
        lines.append("  • Discuss any upcoming risks (earnings, macro events)")

    return "\n".join(lines)
