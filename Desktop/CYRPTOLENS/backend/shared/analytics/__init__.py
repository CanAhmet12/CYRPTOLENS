"""
CryptoLens Analytics Engine
Pure, testable indicator and portfolio metric calculations.
Following Indicator & Analytics Engine Specification exactly.
"""

from .types import Candle
from .indicators.rsi import calculate_rsi
from .indicators.macd import calculate_macd
from .indicators.ema import calculate_ema
from .indicators.volatility import calculate_volatility
from .indicators.trend_score import calculate_trend_score
from .indicators.momentum import calculate_momentum
from .portfolio.portfolio_metrics import (
    calculate_portfolio_value,
    calculate_pnl,
    calculate_allocation,
    calculate_diversification_score,
    calculate_portfolio_volatility,
    calculate_portfolio_risk_score,
)

__all__ = [
    # Types
    "Candle",
    # Indicators
    "calculate_rsi",
    "calculate_macd",
    "calculate_ema",
    "calculate_volatility",
    "calculate_trend_score",
    "calculate_momentum",
    # Portfolio Metrics
    "calculate_portfolio_value",
    "calculate_pnl",
    "calculate_allocation",
    "calculate_diversification_score",
    "calculate_portfolio_volatility",
    "calculate_portfolio_risk_score",
]

