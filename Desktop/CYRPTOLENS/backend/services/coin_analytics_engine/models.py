"""
Pydantic models for Coin Analytics Engine.
Request/Response models for API endpoints.
"""
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class RSIResponse(BaseModel):
    """Response model for RSI endpoint."""
    coin_symbol: str
    rsi: Decimal
    interpretation: str  # "oversold", "neutral", "overbought"
    timestamp: datetime


class MACDResponse(BaseModel):
    """Response model for MACD endpoint."""
    coin_symbol: str
    macd: Decimal
    signal: Decimal
    histogram: Decimal
    interpretation: str  # "bullish", "bearish", "neutral"
    timestamp: datetime


class SupportResistanceResponse(BaseModel):
    """Response model for support/resistance levels endpoint."""
    coin_symbol: str
    support_levels: List[Decimal]
    resistance_levels: List[Decimal]
    current_price: Decimal
    timestamp: datetime


class CoinOverviewResponse(BaseModel):
    """Response model for coin overview endpoint."""
    coin_symbol: str
    current_price: Decimal
    rsi: Decimal
    rsi_interpretation: str
    macd: Decimal
    macd_signal: Decimal
    macd_histogram: Decimal
    macd_interpretation: str
    ema20: Decimal
    ema50: Decimal
    ema200: Decimal
    ema_alignment: str  # "bullish", "bearish", "neutral"
    volatility: Decimal
    momentum: Decimal
    support_levels: List[Decimal]
    resistance_levels: List[Decimal]
    trend_direction: str
    trend_strength: int
    trend_score: Decimal
    timestamp: datetime


class ChartDataResponse(BaseModel):
    """Response model for chart data endpoint."""
    coin_symbol: str
    timeframe: str
    prices: List[dict]  # List of OHLC data: {timestamp: int, open: float, high: float, low: float, close: float, volume: float, price: float}
    timestamp: datetime


# Premium Coin Features Models

class CoinNewsItem(BaseModel):
    """News item model."""
    title: str
    source: str
    url: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    category: Optional[str] = None


class CoinNewsResponse(BaseModel):
    """Response model for coin news endpoint."""
    coin_symbol: str
    news: List[CoinNewsItem]
    total: int


class CoinPricePrediction(BaseModel):
    """Price prediction model."""
    predicted_price: Decimal
    confidence_score: Decimal
    prediction_date: datetime
    timeframe: str
    model_version: Optional[str] = None


class CoinPricePredictionResponse(BaseModel):
    """Response model for price predictions."""
    coin_symbol: str
    predictions: List[CoinPricePrediction]
    current_price: Decimal


class CoinSentiment(BaseModel):
    """Sentiment analysis model."""
    source: str  # twitter, reddit, news
    sentiment_score: Decimal  # -100 to 100
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    total_mentions: int = 0
    recorded_at: datetime


class CoinSentimentResponse(BaseModel):
    """Response model for sentiment analysis."""
    coin_symbol: str
    overall_sentiment: Decimal
    sources: List[CoinSentiment]
    timestamp: datetime


class CoinCorrelationItem(BaseModel):
    """Correlation item model."""
    coin_symbol: str
    correlation: Decimal
    price: Decimal
    change_24h: Decimal


class CoinCorrelationResponse(BaseModel):
    """Response model for correlation analysis."""
    coin_symbol: str
    correlations: List[CoinCorrelationItem]
    timestamp: datetime


class CoinMarketDepthItem(BaseModel):
    """Market depth item model."""
    price: Decimal
    quantity: Decimal
    total: Decimal


class CoinMarketDepthResponse(BaseModel):
    """Response model for market depth."""
    coin_symbol: str
    exchange: str
    bids: List[CoinMarketDepthItem]
    asks: List[CoinMarketDepthItem]
    timestamp: datetime


class CoinTradingPair(BaseModel):
    """Trading pair model."""
    base_symbol: str
    quote_symbol: str
    exchange: str
    volume_24h: Optional[Decimal] = None
    price: Optional[Decimal] = None


class CoinTradingPairsResponse(BaseModel):
    """Response model for trading pairs."""
    coin_symbol: str
    pairs: List[CoinTradingPair]
    timestamp: datetime


class CoinHistoricalPerformance(BaseModel):
    """Historical performance data point."""
    date: datetime
    price: Decimal
    volume: Decimal
    change_24h: Decimal


class CoinHistoricalResponse(BaseModel):
    """Response model for historical performance."""
    coin_symbol: str
    timeframe: str
    data: List[CoinHistoricalPerformance]
    total_return: Decimal
    volatility: Decimal


# Phase 1.1: Coin Dashboard Response Model
class CoinDashboardResponse(BaseModel):
    """Response model for coin dashboard endpoint."""
    overview: Optional[CoinOverviewResponse] = None
    chartData: Optional[ChartDataResponse] = None
    news: Optional[CoinNewsResponse] = None
    portfolioPosition: Optional[dict] = None  # Portfolio position data
    analytics: Optional[dict] = None  # Combined analytics data
    lastUpdated: str
    cacheExpiry: str