"""
API Gateway response models for OpenAPI documentation.
These models define the structure of API responses for better documentation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class MarketOverviewResponse(BaseModel):
    """Market overview data response."""
    total_market_cap: Optional[float] = None
    total_volume_24h: Optional[float] = None
    btc_dominance: Optional[float] = None
    eth_dominance: Optional[float] = None
    market_cap_change_24h: Optional[float] = None
    active_cryptocurrencies: Optional[int] = None


class MarketHeatmapItem(BaseModel):
    """Single item in market heatmap."""
    symbol: str
    name: str
    price: float
    change_24h: float
    market_cap: Optional[float] = None


class MarketHeatmapResponse(BaseModel):
    """Market heatmap data response."""
    data: List[MarketHeatmapItem]
    total_count: int


class MarketDominanceResponse(BaseModel):
    """Market dominance data response."""
    btc_dominance: float
    eth_dominance: float
    other_dominance: float


class FearGreedResponse(BaseModel):
    """Fear & Greed Index response."""
    value: int
    classification: str
    timestamp: Optional[datetime] = None


class VolatilityResponse(BaseModel):
    """Market volatility data response."""
    btc_volatility: Optional[float] = None
    eth_volatility: Optional[float] = None
    market_volatility: Optional[float] = None


class MarketTrendResponse(BaseModel):
    """Market trend data response."""
    trend: str  # "bullish", "bearish", "neutral"
    confidence: Optional[float] = None
    timeframe: Optional[str] = None


class TopMoverItem(BaseModel):
    """Top mover coin item."""
    symbol: str
    name: str
    price: float
    change_24h: float
    volume_24h: Optional[float] = None


class TopMoversResponse(BaseModel):
    """Top movers response."""
    gainers: List[TopMoverItem]
    losers: List[TopMoverItem]


class MarketDashboardResponse(BaseModel):
    """Complete market dashboard response."""
    market: Dict[str, Any]
    exchanges: Optional[Dict[str, Any]] = None
    chains: Optional[Dict[str, Any]] = None
    categories: Optional[Dict[str, Any]] = None
    calendar: Optional[Dict[str, Any]] = None
    realtime: Dict[str, Any]
    lastUpdated: str
    cacheExpiry: str


class PortfolioItemResponse(BaseModel):
    """Portfolio item response."""
    id: str
    coin_symbol: str
    amount: float
    buy_price: float
    current_price: Optional[float] = None
    value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    notes: Optional[str] = None


class PortfolioResponse(BaseModel):
    """Portfolio data response."""
    items: List[PortfolioItemResponse]
    total_value: float
    total_profit_loss: float
    total_profit_loss_percent: float


class CoinOverviewResponse(BaseModel):
    """Coin overview data response."""
    symbol: str
    name: str
    price: float
    change_24h: float
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    description: Optional[str] = None


class CoinChartDataPoint(BaseModel):
    """Single chart data point."""
    timestamp: int
    price: float
    volume: Optional[float] = None


class CoinChartResponse(BaseModel):
    """Coin chart data response."""
    symbol: str
    data: List[CoinChartDataPoint]
    timeframe: str


class AIInsightResponse(BaseModel):
    """AI insight response."""
    insight_type: str  # "market", "portfolio", "coin"
    content: str
    confidence: Optional[float] = None
    generated_at: datetime
    symbols: Optional[List[str]] = None


class WatchlistItemResponse(BaseModel):
    """Watchlist item response."""
    coin_symbol: str
    added_at: datetime


class WatchlistResponse(BaseModel):
    """Watchlist data response."""
    items: List[WatchlistItemResponse]
    total_count: int


class AlertResponse(BaseModel):
    """Alert response."""
    id: str
    coin_symbol: str
    alert_type: str  # "price_above", "price_below", "change_24h"
    target_value: float
    is_active: bool
    triggered_at: Optional[datetime] = None
    created_at: datetime


class AlertsResponse(BaseModel):
    """Alerts list response."""
    alerts: List[AlertResponse]
    total_count: int


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    message: str
    token: Optional[str] = None
    user_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: Optional[str] = None
    version: Optional[str] = None


class ErrorResponseModel(BaseModel):
    """Standard error response model."""
    error: bool = True
    error_code: str
    message: str
    detail: Optional[str] = None

