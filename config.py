"""
config.py — Portfolio Configuration & Risk Thresholds

Edit this file to match your club's actual portfolio.
Tickers use Yahoo Finance format:
  - US stocks:  AAPL, MSFT, GOOGL
  - HK stocks:  0700.HK, 9988.HK
  - A-shares:   600519.SS (Shanghai), 000858.SZ (Shenzhen)
  - ETFs:       SPY, QQQ, 510300.SS
"""

# =============================================================
# PORTFOLIO HOLDINGS
# Each holding: (ticker, shares, cost_per_share_usd)
# =============================================================
HOLDINGS = [
    # US Stocks
    ("AAPL",    50,  178.00),
    ("MSFT",    30,  380.00),
    ("NVDA",    20,  720.00),
    # HK Stocks
    ("0700.HK", 100,  320.00),   # Tencent
    ("9988.HK", 200,   80.00),   # Alibaba (HK)
    # A-Shares
    ("600519.SS", 5, 1680.00),   # Moutai
]

# =============================================================
# SECTOR MAPPING (for concentration analysis)
# =============================================================
SECTORS = {
    "AAPL":      "Technology",
    "MSFT":      "Technology",
    "NVDA":      "Technology",
    "0700.HK":   "Technology",
    "9988.HK":   "E-Commerce",
    "600519.SS": "Consumer",
}

# =============================================================
# BENCHMARK INDEX
# Used for Beta calculation and relative performance
# Examples: "SPY" (S&P500), "^HSI" (Hang Seng), "000300.SS" (CSI300)
# =============================================================
BENCHMARK = "SPY"

# =============================================================
# RISK LIMITS — Thresholds that trigger alerts
# =============================================================
RISK_LIMITS = {
    "max_single_stock_weight": 0.20,   # No single stock > 20% of portfolio
    "max_sector_weight":       0.40,   # No single sector > 40% of portfolio
    "stop_loss_pct":           -0.10,  # Alert if any stock drops 10% from cost
    "max_portfolio_drawdown":  -0.15,  # Alert if portfolio drawdown exceeds 15%
    "max_volatility":          0.30,   # Alert if annualized vol exceeds 30%
}

# =============================================================
# DATA SETTINGS
# =============================================================
LOOKBACK_DAYS = 180   # How many days of history to fetch
RISK_FREE_RATE = 0.04 # Annual risk-free rate (e.g. 4% for US T-bills)
VAR_CONFIDENCE = 0.95 # VaR confidence level
