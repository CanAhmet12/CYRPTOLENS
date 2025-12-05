"""
Pydantic models for AI Insight Service.
Request/Response models for API endpoints.
Following AI Specification exactly.
"""
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from decimal import Decimal
from datetime import datetime


# Market Input DTO (as per specification)
class TopMover(BaseModel):
    """Top gainer/loser model."""
    symbol: str
    change_24h_pct: float


class MarketDataInput(BaseModel):
    """Market data input for AI analysis - exact specification format."""
    market: Dict[str, Any]  # Accepts the full market JSON payload


# Portfolio Input DTO (as per specification)
class PortfolioAssetInput(BaseModel):
    """Portfolio asset input for AI analysis."""
    symbol: str
    weight: float  # 0-1
    volatility: float  # 0-1


class PortfolioDataInput(BaseModel):
    """Portfolio data input for AI analysis - exact specification format."""
    portfolio: Dict[str, Any]  # Accepts the full portfolio JSON payload


# Coin Input DTO (as per specification)
class CoinDataInput(BaseModel):
    """Coin data input for AI analysis - exact specification format."""
    coin: Dict[str, Any]  # Accepts the full coin JSON payload


# Response DTOs (as per specification)
class MarketInsightResponse(BaseModel):
    """Response model for market AI insight - exact specification format."""
    market_summary: str
    risk_comment: str
    # Premium fields
    risk_score: Optional[float] = None  # 0-100
    trend_prediction: Optional[str] = None  # "bullish", "bearish", "neutral"
    confidence_score: Optional[float] = None  # 0-100
    key_opportunities: Optional[List[str]] = None
    key_risks: Optional[List[str]] = None


class PortfolioInsightResponse(BaseModel):
    """Response model for portfolio AI insight - exact specification format."""
    portfolio_summary: str
    risk_summary: str
    # Premium fields
    risk_score: Optional[float] = None  # 0-100
    diversification_score: Optional[float] = None  # 0-100
    performance_score: Optional[float] = None  # 0-100
    recommended_actions: Optional[List[str]] = None
    top_performers: Optional[List[str]] = None
    underperformers: Optional[List[str]] = None


class CoinInsightResponse(BaseModel):
    """Response model for coin AI insight - exact specification format."""
    coin_summary: str
    technical_comment: str
    # Premium fields
    trend_score: Optional[float] = None  # 0-100
    momentum_score: Optional[float] = None  # 0-100
    risk_score: Optional[float] = None  # 0-100
    price_prediction: Optional[str] = None  # "up", "down", "sideways"
    confidence_score: Optional[float] = None  # 0-100
    key_levels: Optional[List[float]] = None  # Support/resistance levels

