"""
Pydantic models for Market Data Service.
Request/Response models for API endpoints.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime


class MarketOverviewResponse(BaseModel):
    """Response model for /market/overview endpoint."""
    total_market_cap: Decimal
    total_volume_24h: Decimal
    btc_dominance: Decimal
    eth_dominance: Decimal
    market_cap_change_24h: Decimal
    active_cryptocurrencies: int
    updated_at: datetime


class CoinData(BaseModel):
    """Individual coin data for heatmap."""
    symbol: str
    name: str
    price: Decimal
    market_cap: Decimal
    volume_24h: Decimal
    price_change_24h: Decimal
    price_change_percentage_24h: Decimal


class HeatmapResponse(BaseModel):
    """Response model for /market/heatmap endpoint."""
    coins: List[CoinData]
    updated_at: datetime


class DominanceResponse(BaseModel):
    """Response model for /market/dominance endpoint."""
    btc_dominance: Decimal
    eth_dominance: Decimal
    other_dominance: Decimal
    updated_at: datetime


class FearGreedResponse(BaseModel):
    """Response model for /market/feargreed endpoint."""
    value: int  # 0-100
    classification: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: datetime


class VolatileCoin(BaseModel):
    """Individual volatile coin data."""
    symbol: str
    volatility: Decimal


class VolatilityResponse(BaseModel):
    """Response model for /market/volatility endpoint."""
    volatility_index: Decimal  # 0-100
    market_volatility: str  # "Low", "Medium", "High", "Extreme"
    btc_volatility: Decimal
    eth_volatility: Decimal
    top_volatile_coins: List[VolatileCoin]
    updated_at: datetime

