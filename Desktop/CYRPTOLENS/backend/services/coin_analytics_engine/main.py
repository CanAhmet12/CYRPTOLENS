"""
Coin Analytics Engine main application.
Implements all coin analytics endpoints as per Technical Specification.
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from shared.config import settings
from shared.database import get_db
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from .service import CoinAnalyticsService
from .models import (
    CoinOverviewResponse,
    RSIResponse,
    MACDResponse,
    SupportResistanceResponse,
    ChartDataResponse,
    CoinNewsResponse,
    CoinNewsItem,
    CoinPricePredictionResponse,
    CoinSentimentResponse,
    CoinCorrelationResponse,
    CoinMarketDepthResponse,
    CoinTradingPairsResponse,
    CoinHistoricalResponse,
    CoinDashboardResponse,  # Phase 1.1: Dashboard response
)

app = FastAPI(
    title="CryptoLens Coin Analytics Engine",
    version=settings.APP_VERSION,
    description="Coin analytics service for CryptoLens - technical indicators and trend analysis"
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
analytics_service = CoinAnalyticsService()


@app.on_event("shutdown")
async def shutdown_event():
    """Close service connections on shutdown."""
    await analytics_service.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "coin_analytics_engine"}


@app.get("/coin/{coin_symbol}/overview", response_model=CoinOverviewResponse)
async def get_coin_overview(
    coin_symbol: str,
    coin_id: str = Query(None, description="CoinGecko coin ID (optional, for better data)"),
    db: Session = Depends(get_db)
):
    """
    Get complete coin analytics overview.
    
    Returns:
    - Current price
    - RSI, MACD, EMA20/50/200
    - Volatility and momentum scores
    - Support/resistance levels
    - Trend direction and strength
    """
    try:
        return await analytics_service.get_coin_overview(
            db, coin_symbol, coin_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get coin overview: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/rsi", response_model=RSIResponse)
async def get_coin_rsi(
    coin_symbol: str,
    coin_id: str = Query(None, description="CoinGecko coin ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Get RSI (Relative Strength Index) for a coin.
    
    RSI interpretation:
    - Overbought: RSI >= 70
    - Oversold: RSI <= 30
    - Neutral: 30 < RSI < 70
    """
    try:
        return await analytics_service.get_rsi(db, coin_symbol, coin_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get RSI: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/macd", response_model=MACDResponse)
async def get_coin_macd(
    coin_symbol: str,
    coin_id: str = Query(None, description="CoinGecko coin ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Get MACD (Moving Average Convergence Divergence) for a coin.
    
    Returns MACD line, signal line, and histogram.
    """
    try:
        return await analytics_service.get_macd(db, coin_symbol, coin_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MACD: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/levels", response_model=SupportResistanceResponse)
async def get_coin_levels(
    coin_symbol: str,
    coin_id: str = Query(None, description="CoinGecko coin ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Get support and resistance levels for a coin.
    
    Returns top 5 support levels (lowest prices) and top 5 resistance levels (highest prices).
    """
    try:
        return await analytics_service.get_support_resistance(
            db, coin_symbol, coin_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get support/resistance levels: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/chart", response_model=ChartDataResponse)
async def get_coin_chart(
    coin_symbol: str,
    timeframe: str = Query(default="1D", description="Timeframe: 1H, 1D, 1W, 1M, 1Y"),
    coin_id: str = Query(None, description="CoinGecko coin ID (optional)"),
    db: Session = Depends(get_db)
):
    """
    Get chart data for a coin with specific timeframe.
    
    Returns historical price data with timestamps for chart visualization.
    """
    try:
        return await analytics_service.get_chart_data(
            db, coin_symbol, timeframe, coin_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chart data: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/news")
async def get_coin_news(
    coin_symbol: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of news items to return"),
    coin_id: str = Query(None, description="CoinGecko coin ID (optional)")
):
    """
    Get news feed for a coin from CoinGecko API.
    
    Returns list of news items with title, source, date, and optional image/URL.
    """
    try:
        import httpx
        from shared.config import settings
        
        # Get coin ID from symbol if not provided
        if not coin_id:
            coin_id = coin_symbol.lower()
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/news"
        params = {
            "limit": limit,
        }
        
        api_key = getattr(settings, 'COINGECKO_API_KEY', '') or ''
        if api_key:
            params["x_cg_demo_api_key"] = api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 404:
                # Coin not found, return empty list
                return {"news": []}
            
            response.raise_for_status()
            data = response.json()
            
            # Format news items
            news_items = []
            for item in data.get("news", [])[:limit]:
                news_items.append({
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                    "url": item.get("url", ""),
                    "image": item.get("image", ""),
                    "description": item.get("description", ""),
                })
            
            return {"news": news_items}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"news": []}
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get news: {str(e)}"
        )
    except Exception as e:
        # Return empty list on error instead of failing
        return {"news": []}


@app.get("/coin/{coin_symbol}/related")
async def get_related_coins(
    coin_symbol: str,
    limit: int = Query(default=5, ge=1, le=20, description="Number of related coins to return")
):
    """
    Get related coins for a coin.
    
    Returns list of related coins with symbol, name, price, and change percent.
    """
    try:
        # Return empty list for now - implement related coins logic in future
        return {"coins": []}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get related coins: {str(e)}"
        )


# Premium Coin Features Endpoints

@app.get("/coin/{coin_symbol}/news", response_model=CoinNewsResponse)
async def get_coin_news_premium(
    coin_symbol: str,
    limit: int = Query(default=20, ge=1, le=50),
    category: str = Query(None, description="Filter by category"),
    source: str = Query(None, description="Filter by source"),
    coin_id: str = Query(None, description="CoinGecko coin ID (optional)")
):
    """
    Get premium news feed for a coin with filtering options.
    
    Returns categorized and filtered news items.
    """
    try:
        return await analytics_service.get_coin_news_premium(
            coin_symbol, limit, category, source, coin_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get coin news: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/predictions", response_model=CoinPricePredictionResponse)
async def get_coin_predictions(
    coin_symbol: str,
    timeframe: str = Query(default="7D", description="Timeframe: 1D, 7D, 30D, 1Y"),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered price predictions for a coin.
    
    Returns predicted prices with confidence scores.
    """
    try:
        return await analytics_service.get_price_predictions(
            db, coin_symbol, timeframe
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get price predictions: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/sentiment", response_model=CoinSentimentResponse)
async def get_coin_sentiment(
    coin_symbol: str,
    db: Session = Depends(get_db)
):
    """
    Get social sentiment analysis for a coin.
    
    Returns sentiment scores from Twitter, Reddit, and news sources.
    """
    try:
        return await analytics_service.get_sentiment_analysis(
            db, coin_symbol
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sentiment: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/correlation", response_model=CoinCorrelationResponse)
async def get_coin_correlation(
    coin_symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get correlation analysis with other coins.
    
    Returns coins with highest correlation to the target coin.
    """
    try:
        return await analytics_service.get_correlation_analysis(
            db, coin_symbol, limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get correlation: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/market-depth", response_model=CoinMarketDepthResponse)
async def get_coin_market_depth(
    coin_symbol: str,
    exchange: str = Query(default="binance", description="Exchange name"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get market depth (order book) for a coin.
    
    Returns bid and ask orders with prices and quantities.
    """
    try:
        return await analytics_service.get_market_depth(
            coin_symbol, exchange, limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get market depth: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/trading-pairs", response_model=CoinTradingPairsResponse)
async def get_coin_trading_pairs(
    coin_symbol: str,
    exchange: str = Query(None, description="Filter by exchange")
):
    """
    Get trading pairs for a coin across exchanges.
    
    Returns available trading pairs with volumes and prices.
    """
    try:
        return await analytics_service.get_trading_pairs(
            coin_symbol, exchange
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trading pairs: {str(e)}"
        )


@app.get("/coin/{coin_symbol}/historical", response_model=CoinHistoricalResponse)
async def get_coin_historical(
    coin_symbol: str,
    timeframe: str = Query(default="1M", description="Timeframe: 7D, 1M, 3M, 6M, 1Y"),
    db: Session = Depends(get_db)
):
    """
    Get historical performance data for a coin.
    
    Returns price history with returns and volatility metrics.
    """
    try:
        return await analytics_service.get_historical_performance(
            db, coin_symbol, timeframe
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get historical data: {str(e)}"
        )
