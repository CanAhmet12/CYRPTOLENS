"""
AI Insight Service main application.
Implements all AI insight endpoints as per AI Specification (v6).
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import asyncio
from datetime import datetime
from shared.config import settings
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from .service import AIInsightService
from .models import (
    MarketDataInput,
    PortfolioDataInput,
    CoinDataInput,
    MarketInsightResponse,
    PortfolioInsightResponse,
    CoinInsightResponse,
)

app = FastAPI(
    title="CryptoLens AI Insight Service",
    version=settings.APP_VERSION,
    description="AI insight generation service for CryptoLens - generates analytical insights for market, portfolio, and coins"
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
ai_service = AIInsightService()


@app.on_event("shutdown")
async def shutdown_event():
    """Close service connections on shutdown."""
    await ai_service.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ai_insight_service"}


@app.post("/ai/market", response_model=MarketInsightResponse)
async def generate_market_insight(market_data: MarketDataInput):
    """
    Generate AI market insight.
    
    Analyzes market conditions and provides:
    - Trend condition interpretation
    - Volatility interpretation
    - Dominance effect
    - Risk notes
    - Overall sentiment summary
    
    NOTE: This is analytical only - no trading advice is provided.
    """
    try:
        return await ai_service.generate_market_insight(market_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate market insight: {str(e)}"
        )


@app.post("/ai/portfolio", response_model=PortfolioInsightResponse)
async def generate_portfolio_insight(portfolio_data: PortfolioDataInput):
    """
    Generate AI portfolio insight.
    
    Analyzes user portfolio and provides:
    - Strong coins identification
    - Weak coins identification
    - Diversification score
    - Risk clusters
    - Missing sectors
    - Clear summary
    
    NOTE: This is analytical only - no trading advice is provided.
    """
    try:
        return await ai_service.generate_portfolio_insight(portfolio_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate portfolio insight: {str(e)}"
        )


@app.post("/ai/coin/{symbol}", response_model=CoinInsightResponse)
async def generate_coin_insight(symbol: str, coin_data: CoinDataInput):
    """
    Generate AI coin insight.
    
    Analyzes individual coin and provides:
    - Coin summary
    - Technical comment
    
    NOTE: This is analytical only - no trading advice is provided.
    
    Input: JSON with "coin" field containing analytics data
    """
    try:
        # Ensure symbol is in the coin data if not present
        if "symbol" not in coin_data.coin:
            coin_data.coin["symbol"] = symbol.upper()
        return await ai_service.generate_coin_insight(coin_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate coin insight: {str(e)}"
        )


# Phase 1.1: AI Insights Dashboard Endpoint
@app.get("/ai/dashboard")
async def get_ai_insights_dashboard(
    request: Request,
    user_id: Optional[str] = Query(None, description="User ID for user-specific insights"),
    include_market: bool = Query(True, description="Include market insights"),
    include_portfolio: bool = Query(True, description="Include portfolio insights"),
    include_coin_cache: bool = Query(True, description="Include recent coin insights cache"),
):
    """
    Comprehensive AI insights dashboard endpoint.
    Returns all AI insights in a single optimized response.
    
    Features:
    - Batch parallel requests
    - Multi-layer caching
    - User-specific data (portfolio insights)
    - Precomputed insights
    - Real-time data indicators
    """
    try:
        return await ai_service.get_insights_dashboard(
            user_id=user_id,
            include_market=include_market,
            include_portfolio=include_portfolio,
            include_coin_cache=include_coin_cache,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI insights dashboard: {str(e)}"
        )

