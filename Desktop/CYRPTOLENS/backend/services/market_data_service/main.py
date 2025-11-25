"""
Market Data Service main application.
Implements all market data endpoints as per Technical Specification.
"""
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from shared.config import settings
from shared.database import get_db
from .service import MarketDataService
from .models import (
    MarketOverviewResponse,
    HeatmapResponse,
    DominanceResponse,
    FearGreedResponse,
    VolatilityResponse
)

app = FastAPI(
    title="CryptoLens Market Data Service",
    version=settings.APP_VERSION,
    description="Market data service for CryptoLens - fetches and caches real-time crypto market data"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize service
market_service = MarketDataService()


@app.on_event("shutdown")
async def shutdown_event():
    """Close service connections on shutdown."""
    await market_service.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "market_data_service"}


@app.get("/market/overview", response_model=MarketOverviewResponse)
async def get_market_overview(db: Session = Depends(get_db)):
    """
    Get market overview.
    
    Returns:
    - Total market cap
    - Total 24h volume
    - BTC and ETH dominance
    - Market cap change 24h
    - Active cryptocurrencies count
    """
    return await market_service.get_market_overview(db)


@app.get("/market/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    limit: int = Query(default=100, ge=1, le=250, description="Number of coins to return"),
    db: Session = Depends(get_db)
):
    """
    Get market heatmap data.
    
    Returns list of coins with:
    - Symbol, name, price
    - Market cap, 24h volume
    - Price change 24h (absolute and percentage)
    """
    return await market_service.get_heatmap(db, limit=limit)


@app.get("/market/dominance", response_model=DominanceResponse)
async def get_dominance(db: Session = Depends(get_db)):
    """
    Get BTC and ETH dominance.
    
    Returns:
    - BTC dominance percentage
    - ETH dominance percentage
    - Other coins dominance percentage
    """
    return await market_service.get_dominance(db)


@app.get("/market/feargreed", response_model=FearGreedResponse)
async def get_fear_greed():
    """
    Get Fear & Greed Index.
    
    Returns:
    - Value (0-100)
    - Classification (Extreme Fear, Fear, Neutral, Greed, Extreme Greed)
    - Timestamp
    """
    return await market_service.get_fear_greed()


@app.get("/market/volatility", response_model=VolatilityResponse)
async def get_volatility(db: Session = Depends(get_db)):
    """
    Get market volatility index.
    
    Returns:
    - Volatility index (0-100)
    - Market volatility level (Low/Medium/High/Extreme)
    - BTC and ETH specific volatility
    - Top 10 most volatile coins
    """
    return await market_service.get_volatility(db)


@app.get("/market/trend")
async def get_market_trend(
    days: int = Query(default=7, ge=1, le=365, description="Number of days for trend data"),
    db: Session = Depends(get_db)
):
    """
    Get market trend data.
    
    Returns array of trend values for the specified number of days.
    Each value represents the market cap change percentage for that day.
    """
    return await market_service.get_market_trend(db, days=days)
