"""
API Gateway routes.
Routes requests to appropriate microservices.
"""
# Standard library imports
import asyncio
import json
from typing import Any, Dict, List, Optional

# Third-party imports
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
import httpx

# Local application imports
from shared.config import settings
from shared.error_models import ErrorCode, create_error_response
from shared.pagination import PaginationParams, PaginatedResponse, get_pagination_params
from .response_models import (
    AIInsightResponse,
    AlertsResponse,
    AuthResponse,
    CoinChartResponse,
    CoinOverviewResponse,
    ErrorResponseModel,
    FearGreedResponse,
    HealthResponse,
    MarketDashboardResponse,
    MarketDominanceResponse,
    MarketHeatmapResponse,
    MarketOverviewResponse,
    MarketTrendResponse,
    PortfolioItemResponse,
    PortfolioResponse,
    VolatilityResponse,
    WatchlistResponse,
)

router = APIRouter()


class BatchRequestItem(BaseModel):
    """Single request in a batch."""
    method: str = "GET"
    path: str
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    id: Optional[str] = None  # Optional ID to match response


class BatchRequest(BaseModel):
    """Batch request containing multiple API calls."""
    requests: List[BatchRequestItem]


async def proxy_request(service_url: str, path: str, method: str = "GET", request: Request = None, **kwargs):
    """Proxy request to a microservice."""
    import httpx
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        url = f"{service_url}{path}"
        
        # Forward Authorization header if present
        headers = {}
        if request:
            auth_header = request.headers.get("Authorization")
            if auth_header:
                headers["Authorization"] = auth_header
        
        try:
            if method == "GET":
                response = await client.get(url, params=kwargs.get("params"), headers=headers)
            elif method == "POST":
                response = await client.post(url, json=kwargs.get("json"), params=kwargs.get("params"), headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, params=kwargs.get("params"), headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors with status codes
            import logging
            logger = logging.getLogger(__name__)
            
            error_detail = "Service error"
            status_code = e.response.status_code if e.response else 503
            
            try:
                if e.response is not None:
                    error_data = e.response.json()
                    error_detail = error_data.get("detail", error_data.get("message", str(e)))
            except:
                error_detail = str(e)
            
            # Map HTTP status codes to error codes
            error_code_map = {
                400: ErrorCode.VALIDATION_ERROR,
                401: ErrorCode.UNAUTHORIZED,
                403: ErrorCode.FORBIDDEN,
                404: ErrorCode.NOT_FOUND,
                409: ErrorCode.RESOURCE_CONFLICT,
                429: ErrorCode.RATE_LIMIT_EXCEEDED,
                500: ErrorCode.INTERNAL_ERROR,
                503: ErrorCode.SERVICE_UNAVAILABLE,
            }
            
            error_code = error_code_map.get(status_code, ErrorCode.INTERNAL_ERROR)
            
            logger.warning(f"HTTP error from {url}: {status_code} - {error_detail}")
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": True,
                    "error_code": error_code.value,
                    "message": error_detail,
                    "detail": f"Service returned {status_code}",
                }
            )
        except httpx.RequestError as e:
            # Handle connection errors
            import logging
            logger = logging.getLogger(__name__)
            error_msg = f"RequestError to {url}: {type(e).__name__} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            raise HTTPException(
                status_code=503,
                detail={
                    "error": True,
                    "error_code": ErrorCode.SERVICE_UNAVAILABLE.value,
                    "message": "Service unavailable",
                    "detail": f"Connection error: {type(e).__name__} - {str(e)}",
                }
            )
        except httpx.HTTPError as e:
            # Handle other HTTP errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"HTTP error to {url}: {str(e)}", exc_info=True)
            
            raise HTTPException(
                status_code=503,
                detail={
                    "error": True,
                    "error_code": ErrorCode.SERVICE_UNAVAILABLE.value,
                    "message": "Service error",
                    "detail": str(e),
                }
            )


# Market API routes
@router.get(
    "/market/overview",
    response_model=MarketOverviewResponse,
    summary="Get market overview",
    description="Retrieve overall cryptocurrency market statistics including total market cap, volume, and dominance metrics.",
    tags=["Market"],
    responses={
        200: {"description": "Market overview data retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def market_overview():
    """
    Get market overview data.
    
    Returns:
        MarketOverviewResponse: Market statistics including:
        - Total market capitalization
        - 24h trading volume
        - BTC and ETH dominance percentages
        - Market cap change in 24h
        - Number of active cryptocurrencies
    """
    return await proxy_request(settings.MARKET_SERVICE_URL, "/market/overview")


@router.get(
    "/market/heatmap",
    response_model=MarketHeatmapResponse,
    summary="Get market heatmap",
    description="Retrieve cryptocurrency market heatmap data showing price changes and market performance.",
    tags=["Market"],
    responses={
        200: {"description": "Market heatmap data retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def market_heatmap(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of coins to return in heatmap",
        example=250,
    )
):
    """
    Get market heatmap data.
    
    Args:
        limit: Maximum number of coins to include in the heatmap (1-1000, default: 100)
    
    Returns:
        MarketHeatmapResponse: Heatmap data with coin symbols, prices, and 24h changes
    """
    return await proxy_request(
        settings.MARKET_SERVICE_URL,
        "/market/heatmap",
        params={"limit": limit}
    )


@router.get(
    "/market/dominance",
    response_model=MarketDominanceResponse,
    summary="Get market dominance",
    description="Retrieve cryptocurrency market dominance metrics for BTC, ETH, and other coins.",
    tags=["Market"],
    responses={
        200: {"description": "Market dominance data retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def market_dominance():
    """
    Get market dominance data.
    
    Returns:
        MarketDominanceResponse: Dominance percentages for:
        - Bitcoin (BTC)
        - Ethereum (ETH)
        - Other cryptocurrencies
    """
    return await proxy_request(settings.MARKET_SERVICE_URL, "/market/dominance")


@router.get(
    "/market/feargreed",
    response_model=FearGreedResponse,
    summary="Get Fear & Greed Index",
    description="Retrieve the current Fear & Greed Index value and classification for the cryptocurrency market.",
    tags=["Market"],
    responses={
        200: {"description": "Fear & Greed Index retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def market_feargreed():
    """
    Get Fear & Greed Index.
    
    Returns:
        FearGreedResponse: Current Fear & Greed Index with:
        - Value (0-100)
        - Classification (e.g., "Extreme Fear", "Greed")
        - Timestamp
    """
    return await proxy_request(settings.MARKET_SERVICE_URL, "/market/feargreed")


@router.get(
    "/market/volatility",
    response_model=VolatilityResponse,
    summary="Get market volatility",
    description="Retrieve volatility metrics for major cryptocurrencies and the overall market.",
    tags=["Market"],
    responses={
        200: {"description": "Market volatility data retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def market_volatility():
    """
    Get market volatility data.
    
    Returns:
        VolatilityResponse: Volatility metrics for:
        - Bitcoin (BTC)
        - Ethereum (ETH)
        - Overall market
    """
    return await proxy_request(settings.MARKET_SERVICE_URL, "/market/volatility")


@router.get(
    "/market/trend",
    response_model=MarketTrendResponse,
    summary="Get market trend",
    description="Retrieve market trend analysis for the specified time period.",
    tags=["Market"],
    responses={
        200: {"description": "Market trend data retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def market_trend(
    days: int = Query(
        default=7,
        ge=1,
        le=365,
        description="Number of days for trend analysis",
        example=7,
    )
):
    """
    Get market trend data.
    
    Args:
        days: Number of days to analyze (1-365, default: 7)
    
    Returns:
        MarketTrendResponse: Trend analysis with:
        - Trend direction ("bullish", "bearish", "neutral")
        - Confidence level (0-1)
        - Timeframe
    """
    return await proxy_request(
        settings.MARKET_SERVICE_URL,
        "/market/trend",
        params={"days": days}
    )


@router.get("/market/exchanges")
async def market_exchanges(exchange_type: str = "all"):
    """Proxy to Market Data Service - /market/exchanges"""
    return await proxy_request(
        settings.MARKET_SERVICE_URL,
        "/market/exchanges",
        params={"exchange_type": exchange_type}
    )


@router.get("/market/chains")
async def market_chains():
    """Proxy to Market Data Service - /market/chains"""
    return await proxy_request(
        settings.MARKET_SERVICE_URL,
        "/market/chains"
    )


@router.get("/market/categories")
async def market_categories():
    """Proxy to Market Data Service - /market/categories"""
    return await proxy_request(
        settings.MARKET_SERVICE_URL,
        "/market/categories"
    )


@router.get("/market/calendar")
async def get_market_calendar():
    """Proxy to Market Data Service - GET /market/calendar"""
    return await proxy_request(
        settings.MARKET_SERVICE_URL,
        "/market/calendar"
    )


# Market Dashboard API route - Phase 1.1: Complete Market Dashboard Endpoint
@router.get(
    "/market/dashboard",
    response_model=MarketDashboardResponse,
    summary="Get market dashboard",
    description="Retrieve aggregated market dashboard data including overview, heatmap, dominance, and real-time metrics in a single response.",
    tags=["Market"],
    responses={
        200: {"description": "Market dashboard data retrieved successfully"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def get_market_dashboard(
    request: Request = None,
    limit: int = Query(
        default=250,
        ge=1,
        le=1000,
        description="Number of coins to fetch in heatmap",
        example=250,
    ),
):
    """
    Get aggregated market dashboard data.
    Returns all data needed for the market page in a single response.
    Uses batch request internally for optimal performance.
    
    Phase 1.1 Implementation:
    - Parallel batch requests (async/await)
    - Multi-layer caching (L1/L2) with user-specific keys
    - Precomputed top movers, trending coins, market trends
    - Error handling with graceful degradation
    - Stale cache fallback
    - Response optimization (field selection, compression-ready)
    - Real-time data integration (WebSocket status, last update timestamp)
    
    Args:
        request: FastAPI Request object (for auth header)
        limit: Number of coins to fetch in heatmap (default: 250)
    
    Returns:
        {
            "market": {
                "overview": {...},
                "heatmap": {...},
                "dominance": {...},
                "fearGreed": {...},
                "volatility": {...},
                "trend": {...},
                "topMovers": {
                    "gainers": [...],
                    "losers": [...]
                },
                "trending": [...]
            },
            "exchanges": {...},  # Optional
            "chains": {...},     # Optional
            "categories": {...}, # Optional
            "calendar": {...},   # Optional
            "realtime": {
                "websocketStatus": "connected" | "disconnected",
                "lastUpdate": "2024-01-01T00:00:00Z",
                "dataFreshness": "fresh" | "stale" | "cached"
            },
            "lastUpdated": "2024-01-01T00:00:00Z",
            "cacheExpiry": "2024-01-01T00:01:00Z"
        }
    """
    from datetime import datetime, timedelta
    from shared.cache_manager import get_cache_manager
    from shared.redis_client import get_redis
    import json
    import logging
    import httpx
    
    logger = logging.getLogger(__name__)
    cache_manager = get_cache_manager()
    redis_client = get_redis()
    
    # User-specific cache key (for watchlist/preferences if authenticated)
    auth_header = None
    user_cache_key = f"market:dashboard:{limit}"
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            user_cache_key = f"market:dashboard:{limit}:{hash(auth_header) % 10000}"
    
    # Try to get from multi-layer cache first (L1 -> L2)
    cached_data = cache_manager.get(user_cache_key, ttl_l1=30, ttl_l2=60)
    if cached_data:
        logger.debug(f"Cache HIT for {user_cache_key}")
        # Update freshness indicator
        if isinstance(cached_data, dict):
            cached_data["realtime"] = cached_data.get("realtime", {})
            cached_data["realtime"]["dataFreshness"] = "cached"
        return cached_data
    
    # Build batch request for all market page data
    batch_requests = [
        BatchRequestItem(method="GET", path="/market/overview", id="overview"),
        BatchRequestItem(method="GET", path="/market/heatmap", params={"limit": limit}, id="heatmap"),
        BatchRequestItem(method="GET", path="/market/dominance", id="dominance"),
        BatchRequestItem(method="GET", path="/market/feargreed", id="feargreed"),
        BatchRequestItem(method="GET", path="/market/volatility", id="volatility"),
        BatchRequestItem(method="GET", path="/market/trend", params={"days": 7}, id="trend"),
    ]
    
    # Add user-specific requests if authenticated (watchlist for filtering)
    if auth_header:
        batch_requests.append(
            BatchRequestItem(method="GET", path="/watchlist", id="watchlist")
        )
    
    # Execute batch request with error handling
    batch = BatchRequest(requests=batch_requests)
    try:
        batch_result = await batch_request(batch, request=request)
    except Exception as e:
        logger.error(f"Batch request failed: {e}")
        # Fallback: Try to return cached data even if stale
        cached_data = cache_manager.get(user_cache_key, ttl_l1=0, ttl_l2=0)  # Accept stale data
        if cached_data:
            logger.warning(f"Returning stale cache due to batch request failure")
            if isinstance(cached_data, dict):
                cached_data["realtime"] = cached_data.get("realtime", {})
                cached_data["realtime"]["dataFreshness"] = "stale"
            return cached_data
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    # Process results with graceful degradation
    results_dict = {r["id"]: r for r in batch_result["results"]}
    
    # Extract and process data (with fallbacks)
    def safe_get(result_key: str, default: Any = None):
        """Safely get result data with fallback."""
        result = results_dict.get(result_key, {})
        if result.get("status", 0) >= 400:
            logger.warning(f"Request {result_key} failed: {result.get('error', 'Unknown error')}")
            return default
        return result.get("data", default)
    
    market_overview = safe_get("overview", {})
    heatmap_data = safe_get("heatmap", {})
    dominance_data = safe_get("dominance", {})
    feargreed_data = safe_get("feargreed", {})
    volatility_data = safe_get("volatility", {})
    trend_data = safe_get("trend", {})
    watchlist_data = safe_get("watchlist") if auth_header else None
    
    # Phase 1.1: Precomputed Top Movers (from heatmap)
    coins = heatmap_data.get("coins", []) if heatmap_data else []
    
    # FIX: Convert price_change_percentage_24h to float to avoid TypeError
    def safe_float(value, default=0.0):
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    top_gainers = sorted(
        [c for c in coins if safe_float(c.get("price_change_percentage_24h", 0)) > 0],
        key=lambda x: safe_float(x.get("price_change_percentage_24h", 0)),
        reverse=True
    )[:10] if coins else []
    
    top_losers = sorted(
        [c for c in coins if safe_float(c.get("price_change_percentage_24h", 0)) < 0],
        key=lambda x: safe_float(x.get("price_change_percentage_24h", 0))
    )[:10] if coins else []
    
    # Phase 1.1: Precomputed Trending Coins (by volume change or other metrics)
    trending_coins = sorted(
        coins,
        key=lambda x: (
            x.get("total_volume", 0) * abs(x.get("price_change_percentage_24h", 0))
        ),
        reverse=True
    )[:10] if coins else []
    
    # Phase 1.1: Precomputed Market Trends (from trend data)
    market_trends = {}
    if trend_data:
        # Calculate trend indicators
        trend_scores = trend_data.get("scores", []) if isinstance(trend_data, dict) else []
        if trend_scores:
            market_trends = {
                "trendStrength": sum(trend_scores) / len(trend_scores) if trend_scores else 50,
                "trendDirection": "bullish" if (sum(trend_scores) / len(trend_scores)) > 50 else "bearish",
                "trendScore": sum(trend_scores) / len(trend_scores) if trend_scores else 50,
            }
    
    # Phase 1.1: Real-time Data Integration
    websocket_status = "disconnected"  # Default
    try:
        # Check WebSocket service health
        realtime_service_url = settings.REALTIME_SERVICE_URL
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
            health_response = await client.get(f"{realtime_service_url}/health")
            if health_response.status_code == 200:
                websocket_status = "connected"
    except Exception:
        pass  # WebSocket service may not be available
    
    # Build response with optimized fields
    response = {
        "market": {
            "overview": market_overview,
            "heatmap": heatmap_data,
            "dominance": dominance_data,
            "fearGreed": feargreed_data,
            "volatility": volatility_data,
            "trend": trend_data,
            "topMovers": {
                "gainers": top_gainers,
                "losers": top_losers,
            },
            "trending": trending_coins,
            "trends": market_trends,
        },
        "watchlist": watchlist_data if auth_header else None,
        "realtime": {
            "websocketStatus": websocket_status,
            "lastUpdate": datetime.utcnow().isoformat() + "Z",
            "dataFreshness": "fresh",
        },
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "cacheExpiry": (datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z",
    }
    
    # Cache response using multi-layer cache (L1 + L2)
    try:
        cache_manager.set(user_cache_key, response, ttl_l1=30, ttl_l2=60)
    except Exception as e:
        logger.warning(f"Failed to cache response: {e}")
    
    return response


# Portfolio API routes
@router.get(
    "/portfolio",
    response_model=PortfolioResponse,
    summary="Get user portfolio",
    description="Retrieve the authenticated user's cryptocurrency portfolio with current values and profit/loss calculations.",
    tags=["Portfolio"],
    responses={
        200: {"description": "Portfolio data retrieved successfully"},
        401: {"model": ErrorResponseModel, "description": "Unauthorized - Authentication required"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def get_portfolio(request: Request):
    """
    Get user portfolio.
    
    Requires authentication via Authorization header.
    
    Returns:
        PortfolioResponse: User's portfolio including:
        - List of portfolio items with current prices
        - Total portfolio value
        - Total profit/loss (absolute and percentage)
    """
    return await proxy_request(settings.PORTFOLIO_SERVICE_URL, "/portfolio", request=request)


@router.post(
    "/portfolio/add",
    response_model=PortfolioItemResponse,
    summary="Add portfolio item",
    description="Add a new cryptocurrency to the user's portfolio.",
    tags=["Portfolio"],
    responses={
        200: {"description": "Portfolio item added successfully"},
        400: {"model": ErrorResponseModel, "description": "Invalid request data"},
        401: {"model": ErrorResponseModel, "description": "Unauthorized - Authentication required"},
        503: {"model": ErrorResponseModel, "description": "Service unavailable"},
    },
)
async def add_portfolio_item(item: dict, request: Request):
    """
    Add a new item to the portfolio.
    
    Requires authentication via Authorization header.
    
    Request body should include:
        - coin_symbol: Cryptocurrency symbol (e.g., "BTC")
        - amount: Amount of cryptocurrency
        - buy_price: Purchase price per unit
        - notes: Optional notes about the purchase
    
    Returns:
        PortfolioItemResponse: The newly created portfolio item
    """
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/add",
        method="POST",
        request=request,
        json=item
    )


@router.post("/portfolio/edit")
async def edit_portfolio_item(
    item_id: str,
    request: Request,
    amount: float = None,
    buy_price: float = None
):
    """Proxy to Portfolio Service - POST /portfolio/edit"""
    params = {"item_id": item_id}
    if amount is not None:
        params["amount"] = amount
    if buy_price is not None:
        params["buy_price"] = buy_price
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/edit",
        method="POST",
        request=request,
        params=params
    )


@router.delete("/portfolio/remove")
async def remove_portfolio_item(item_id: str, request: Request):
    """Proxy to Portfolio Service - DELETE /portfolio/remove"""
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/remove",
        method="DELETE",
        request=request,
        params={"item_id": item_id}
    )


@router.get("/portfolio/performance")
async def get_portfolio_performance(timeframe: str = "1D", request: Request = None):
    """Proxy to Portfolio Service - GET /portfolio/performance"""
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/performance",
        request=request,
        params={"timeframe": timeframe}
    )


@router.get("/portfolio/transactions")
async def get_transaction_history(limit: int = 50, request: Request = None):
    """Proxy to Portfolio Service - GET /portfolio/transactions"""
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/transactions",
        request=request,
        params={"limit": limit}
    )


# Portfolio Premium Features API routes
@router.get("/portfolio/wallets")
async def get_wallets(request: Request):
    """Proxy to Portfolio Service - GET /portfolio/wallets"""
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/wallets",
        request=request
    )


@router.post("/portfolio/wallets")
async def create_wallet(wallet: dict, request: Request):
    """Proxy to Portfolio Service - POST /portfolio/wallets"""
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/wallets",
        method="POST",
        request=request,
        json=wallet
    )


@router.get("/portfolio/analytics/sharpe-ratio")
async def get_sharpe_ratio(
    timeframe: str = "30D",
    wallet_id: str = None,
    request: Request = None
):
    """Proxy to Portfolio Service - GET /portfolio/analytics/sharpe-ratio"""
    params = {"timeframe": timeframe}
    if wallet_id:
        params["wallet_id"] = wallet_id
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/analytics/sharpe-ratio",
        request=request,
        params=params
    )


@router.get("/portfolio/analytics/alpha-beta")
async def get_alpha_beta(
    benchmark: str = "BTC",
    timeframe: str = "30D",
    wallet_id: str = None,
    request: Request = None
):
    """Proxy to Portfolio Service - GET /portfolio/analytics/alpha-beta"""
    params = {"benchmark": benchmark, "timeframe": timeframe}
    if wallet_id:
        params["wallet_id"] = wallet_id
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/analytics/alpha-beta",
        request=request,
        params=params
    )


@router.get("/portfolio/tax/realized-unrealized")
async def get_realized_unrealized(
    wallet_id: str = None,
    request: Request = None
):
    """Proxy to Portfolio Service - GET /portfolio/tax/realized-unrealized"""
    params = {}
    if wallet_id:
        params["wallet_id"] = wallet_id
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/tax/realized-unrealized",
        request=request,
        params=params
    )


@router.get("/portfolio/rebalancing/suggestions")
async def get_rebalancing_suggestions(
    wallet_id: str = None,
    request: Request = None
):
    """Proxy to Portfolio Service - GET /portfolio/rebalancing/suggestions"""
    params = {}
    if wallet_id:
        params["wallet_id"] = wallet_id
    return await proxy_request(
        settings.PORTFOLIO_SERVICE_URL,
        "/portfolio/rebalancing/suggestions",
        request=request,
        params=params
    )


# Coin Analytics API routes
@router.get("/coin/{coin_symbol}/overview")
async def get_coin_overview(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/overview"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/overview",
        params=params
    )


@router.get("/coin/{coin_symbol}/rsi")
async def get_coin_rsi(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/rsi"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/rsi",
        params=params
    )


@router.get("/coin/{coin_symbol}/macd")
async def get_coin_macd(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/macd"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/macd",
        params=params
    )


@router.get("/coin/{coin_symbol}/levels")
async def get_coin_levels(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/levels"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/levels",
        params=params
    )


@router.get("/coin/{coin_symbol}/chart")
async def get_coin_chart(coin_symbol: str, timeframe: str = "1D", coin_id: str = None, request: Request = None):
    """Proxy to Coin Analytics Engine - GET /coin/{symbol}/chart"""
    params = {"timeframe": timeframe}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/chart",
        request=request,
        params=params
    )


# Phase 1.1: Coin Detail Dashboard API route
@router.get("/coin/{coin_symbol}/dashboard")
async def get_coin_dashboard(
    coin_symbol: str,
    coin_id: str = None,
    timeframe: str = "1D",
    include_news: bool = True,
    include_portfolio: bool = True,
    include_analytics: bool = True,
    request: Request = None
):
    """
    Get comprehensive coin dashboard data in a single request.
    Phase 1.1: Batch requests, parallel execution, caching.
    """
    params = {
        "timeframe": timeframe,
        "include_news": str(include_news).lower(),
        "include_portfolio": str(include_portfolio).lower(),
        "include_analytics": str(include_analytics).lower(),
    }
    if coin_id:
        params["coin_id"] = coin_id
    
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/dashboard",
        request=request,
        params=params
    )


# Analytics API routes (alternative paths for backward compatibility)
@router.get("/analytics/coin/{coin_symbol}/overview")
async def get_analytics_coin_overview(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/overview (via /analytics path)"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/overview",
        params=params
    )


@router.get("/analytics/coin/{coin_symbol}/rsi")
async def get_analytics_coin_rsi(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/rsi (via /analytics path)"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/rsi",
        params=params
    )


@router.get("/analytics/coin/{coin_symbol}/macd")
async def get_analytics_coin_macd(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/macd (via /analytics path)"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/macd",
        params=params
    )


@router.get("/analytics/coin/{coin_symbol}/levels")
async def get_analytics_coin_levels(coin_symbol: str, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{id}/levels (via /analytics path)"""
    params = {}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/levels",
        params=params
    )


@router.get("/analytics/coin/{coin_symbol}/chart")
async def get_analytics_coin_chart(coin_symbol: str, timeframe: str = "1D", coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{symbol}/chart (via /analytics path)"""
    params = {"timeframe": timeframe}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/chart",
        params=params
    )


@router.get("/coin/{coin_symbol}/news")
async def get_coin_news(coin_symbol: str, limit: int = 10, coin_id: str = None):
    """Proxy to Coin Analytics Engine - GET /coin/{symbol}/news"""
    params = {"limit": limit}
    if coin_id:
        params["coin_id"] = coin_id
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/news",
        params=params
    )


@router.get("/coin/{coin_symbol}/related")
async def get_related_coins(coin_symbol: str, limit: int = 5):
    """Proxy to Coin Analytics Engine - GET /coin/{symbol}/related"""
    return await proxy_request(
        settings.ANALYTICS_SERVICE_URL,
        f"/coin/{coin_symbol}/related",
        params={"limit": limit}
    )


# Auth API routes
@router.post("/auth/register")
async def register(request: Request):
    """Proxy to Auth Service - POST /auth/register"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.AUTH_SERVICE_URL,
        "/auth/register",
        method="POST",
        json=body
    )


@router.post("/auth/login")
async def login(request: Request):
    """Proxy to Auth Service - POST /auth/login"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.AUTH_SERVICE_URL,
        "/auth/login",
        method="POST",
        json=body
    )


@router.post("/auth/reset")
async def reset_password(request: Request):
    """Proxy to Auth Service - POST /auth/reset"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.AUTH_SERVICE_URL,
        "/auth/reset",
        method="POST",
        json=body
    )


@router.post("/auth/reset/confirm")
async def confirm_password_reset(request: Request):
    """Proxy to Auth Service - POST /auth/reset/confirm"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.AUTH_SERVICE_URL,
        "/auth/reset/confirm",
        method="POST",
        json=body
    )


@router.post("/auth/verify/email")
async def send_verification_email(request: Request):
    """Proxy to Auth Service - POST /auth/verify/email"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.AUTH_SERVICE_URL,
        "/auth/verify/email",
        method="POST",
        json=body
    )


@router.post("/auth/verify/email/confirm")
async def confirm_email_verification(request: Request):
    """Proxy to Auth Service - POST /auth/verify/email/confirm"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.AUTH_SERVICE_URL,
        "/auth/verify/email/confirm",
        method="POST",
        json=body
    )


# AI API routes (v6)
@router.post("/ai/market")
async def generate_market_insight(market_data: dict):
    """Proxy to AI Insight Service - POST /ai/market"""
    return await proxy_request(
        settings.AI_SERVICE_URL,
        "/ai/market",
        method="POST",
        json=market_data
    )


@router.post("/ai/portfolio")
async def generate_portfolio_insight(portfolio_data: dict):
    """Proxy to AI Insight Service - POST /ai/portfolio"""
    return await proxy_request(
        settings.AI_SERVICE_URL,
        "/ai/portfolio",
        method="POST",
        json=portfolio_data
    )


@router.post("/ai/coin/{symbol}")
async def generate_coin_insight(symbol: str, coin_data: dict):
    """Proxy to AI Insight Service - POST /ai/coin/{symbol}"""
    return await proxy_request(
        settings.AI_SERVICE_URL,
        f"/ai/coin/{symbol}",
        method="POST",
        json=coin_data
    )


# Watchlist API routes
@router.get("/watchlist")
async def get_watchlist(request: Request):
    """Proxy to Watchlist Service - GET /watchlist"""
    return await proxy_request(settings.WATCHLIST_SERVICE_URL, "/watchlist", request=request)


@router.post("/watchlist/add")
async def add_watchlist_item(item: dict, request: Request):
    """Proxy to Watchlist Service - POST /watchlist/add"""
    return await proxy_request(
        settings.WATCHLIST_SERVICE_URL,
        "/watchlist/add",
        method="POST",
        request=request,
        json=item
    )


@router.delete("/watchlist/remove/{coin_symbol}")
async def remove_watchlist_item(coin_symbol: str, request: Request):
    """Proxy to Watchlist Service - DELETE /watchlist/remove/{coin_symbol}"""
    return await proxy_request(
        settings.WATCHLIST_SERVICE_URL,
        f"/watchlist/remove/{coin_symbol}",
        method="DELETE",
        request=request
    )


@router.get("/watchlist/check/{coin_symbol}")
async def check_watchlist(coin_symbol: str, request: Request):
    """Proxy to Watchlist Service - GET /watchlist/check/{coin_symbol}"""
    return await proxy_request(
        settings.WATCHLIST_SERVICE_URL,
        f"/watchlist/check/{coin_symbol}",
        request=request
    )


# Alert API routes
@router.get("/alerts")
async def get_alerts(request: Request):
    """Proxy to Alert Service - GET /alerts"""
    return await proxy_request(settings.ALERT_SERVICE_URL, "/alerts", request=request)


@router.post("/alerts")
async def create_alert(alert_data: dict, request: Request):
    """Proxy to Alert Service - POST /alerts"""
    return await proxy_request(
        settings.ALERT_SERVICE_URL,
        "/alerts",
        method="POST",
        request=request,
        json=alert_data
    )


@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, alert_data: dict, request: Request):
    """Proxy to Alert Service - PUT /alerts/{alert_id}"""
    return await proxy_request(
        settings.ALERT_SERVICE_URL,
        f"/alerts/{alert_id}",
        method="PUT",
        request=request,
        json=alert_data
    )


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, request: Request):
    """Proxy to Alert Service - DELETE /alerts/{alert_id}"""
    return await proxy_request(
        settings.ALERT_SERVICE_URL,
        f"/alerts/{alert_id}",
        method="DELETE",
        request=request
    )


@router.get("/alerts/history")
async def get_alert_history(request: Request):
    """Proxy to Alert Service - GET /alerts/history"""
    return await proxy_request(
        settings.ALERT_SERVICE_URL,
        "/alerts/history",
        request=request
    )


# Real-time API routes
@router.get("/realtime/market-overview")
async def get_realtime_market_overview():
    """Get real-time market overview with lastUpdated and isStale"""
    return await proxy_request(
        settings.REALTIME_SERVICE_URL,
        "/realtime/market-overview"
    )


@router.get("/realtime/coin/{symbol}")
async def get_realtime_coin_data(symbol: str, timeframe: str = "1h"):
    """Get real-time data for a coin with lastUpdated and isStale"""
    return await proxy_request(
        settings.REALTIME_SERVICE_URL,
        f"/realtime/coin/{symbol}",
        params={"timeframe": timeframe}
    )


@router.get("/realtime/ticker/{symbol}")
async def get_realtime_ticker(symbol: str):
    """Get latest ticker data for a symbol"""
    return await proxy_request(
        settings.REALTIME_SERVICE_URL,
        f"/realtime/ticker/{symbol}"
    )


@router.get("/realtime/tickers")
async def get_all_realtime_tickers():
    """Get all ticker data"""
    return await proxy_request(
        settings.REALTIME_SERVICE_URL,
        "/realtime/tickers"
    )


@router.get("/health/data")
async def health_data():
    """Get data health information"""
    return await proxy_request(
        settings.REALTIME_SERVICE_URL,
        "/health/data"
    )


# AI Insights Dashboard API route - Phase 1.1: Proxy to AI Insight Service
@router.get("/ai/dashboard")
@router.get("/ai-insights/dashboard")  # Backward compatibility
async def get_ai_insights_dashboard(
    request: Request = None,
    user_id: Optional[str] = None,
    include_market: bool = True,
    include_portfolio: bool = True,
    include_coin_cache: bool = True,
):
    """
    Get aggregated AI insights dashboard data.
    Returns all AI insights needed for the AI Insights page in a single response.
    Uses caching for optimal performance.
    
    Phase 1.1: Proxy to AI Insight Service /ai/dashboard endpoint
    """
    # Proxy to AI Insight Service
    params = {
        "include_market": include_market,
        "include_portfolio": include_portfolio,
        "include_coin_cache": include_coin_cache,
    }
    if user_id:
        params["user_id"] = user_id
    
    return await proxy_request(
        settings.AI_SERVICE_URL,
        "/ai/dashboard",
        request=request,
        params=params
    )


# Home Dashboard API route - Enhanced with AI Insight
@router.get("/home/dashboard")
async def get_home_dashboard(request: Request = None):
    """
    Get aggregated home dashboard data.
    Returns all data needed for the home page in a single response.
    Uses batch request internally for optimal performance.
    Enhanced with AI Insight integration, Portfolio Advanced Metrics, Real-time Data, Error Handling, and Response Optimization.
    
    Phase 1.1 Enhancements:
    - AI Insight auto-generation (if cache miss or stale > 5 minutes)
    - Portfolio Advanced Metrics Integration (Sharpe Ratio, Alpha/Beta)
    - Real-time Data Integration (WebSocket status, last update timestamp)
    - Error Handling & Fallbacks (graceful degradation)
    - Response Optimization (field selection, compression-ready)
    """
    from datetime import datetime, timedelta
    from shared.cache_manager import get_cache_manager
    from shared.redis_client import get_redis
    import json
    import logging
    import httpx
    
    logger = logging.getLogger(__name__)
    cache_manager = get_cache_manager()
    redis_client = get_redis()
    
    # User-specific cache key
    auth_header = None
    user_cache_key = "home:dashboard"
    if request:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            user_cache_key = f"home:dashboard:{hash(auth_header) % 10000}"
    
    # Try to get from multi-layer cache first (L1 -> L2 -> L3)
    cached_data = cache_manager.get(user_cache_key, ttl_l1=30, ttl_l2=60)
    if cached_data:
        logger.debug(f"Cache HIT for {user_cache_key}")
        return cached_data
    
    # Build batch request for all home page data
    batch_requests = [
        BatchRequestItem(method="GET", path="/market/overview", id="overview"),
        BatchRequestItem(method="GET", path="/market/heatmap", params={"limit": 100}, id="heatmap"),
        BatchRequestItem(method="GET", path="/market/dominance", id="dominance"),
        BatchRequestItem(method="GET", path="/market/feargreed", id="feargreed"),
        BatchRequestItem(method="GET", path="/market/volatility", id="volatility"),
    ]
    
    # Add user-specific requests if authenticated
    if auth_header:
        batch_requests.extend([
            BatchRequestItem(method="GET", path="/portfolio", id="portfolio"),
            BatchRequestItem(method="GET", path="/watchlist", id="watchlist"),
            # Phase 1.1: Portfolio Advanced Metrics Integration
            BatchRequestItem(method="GET", path="/portfolio/analytics/sharpe-ratio", params={"timeframe": "30D"}, id="sharpeRatio"),
            BatchRequestItem(method="GET", path="/portfolio/analytics/alpha-beta", params={"benchmark": "BTC", "timeframe": "30D"}, id="alphaBeta"),
        ])
    
    # Execute batch request with error handling
    batch = BatchRequest(requests=batch_requests)
    try:
        batch_result = await batch_request(batch, request=request)
    except Exception as e:
        logger.error(f"Batch request failed: {e}")
        # Fallback: Try to return cached data even if stale
        cached_data = cache_manager.get(user_cache_key, ttl_l1=0, ttl_l2=0)  # Accept stale data
        if cached_data:
            logger.warning(f"Returning stale cache due to batch request failure")
            return cached_data
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    # Process results with graceful degradation
    results_dict = {r["id"]: r for r in batch_result["results"]}
    
    # Extract and process data (with fallbacks)
    def safe_get(result_key: str, default: Any = None):
        """Safely get result data with fallback."""
        result = results_dict.get(result_key, {})
        if result.get("status", 0) >= 400:
            logger.warning(f"Request {result_key} failed: {result.get('error', 'Unknown error')}")
            return default
        return result.get("data", default)
    
    market_overview = safe_get("overview", {})
    heatmap_data = safe_get("heatmap", {})
    dominance_data = safe_get("dominance", {})
    feargreed_data = safe_get("feargreed", {})
    volatility_data = safe_get("volatility", {})
    portfolio_data = safe_get("portfolio") if auth_header else None
    watchlist_data = safe_get("watchlist") if auth_header else None
    sharpe_ratio_data = safe_get("sharpeRatio") if auth_header else None
    alpha_beta_data = safe_get("alphaBeta") if auth_header else None
    
    # Calculate top gainers and losers from heatmap (with fallback)
    coins = heatmap_data.get("coins", []) if heatmap_data else []
    
    # FIX: Convert price_change_percentage_24h to float to avoid TypeError
    def safe_float(value, default=0.0):
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    top_gainers = sorted(
        [c for c in coins if safe_float(c.get("price_change_percentage_24h", 0)) > 0],
        key=lambda x: safe_float(x.get("price_change_percentage_24h", 0)),
        reverse=True
    )[:5] if coins else []
    
    top_losers = sorted(
        [c for c in coins if safe_float(c.get("price_change_percentage_24h", 0)) < 0],
        key=lambda x: safe_float(x.get("price_change_percentage_24h", 0))
    )[:5] if coins else []
    
    # Phase 1.1: AI Insight auto-generation (if cache miss or stale > 5 minutes)
    ai_insight = None
    if auth_header:
        try:
            ai_cache_key = f"ai_insights:market:{hash(auth_header) % 10000}"
            cached_ai = redis_client.get(ai_cache_key)
            
            # Check if AI insight exists and is fresh (< 5 minutes)
            should_generate = False
            if cached_ai:
                try:
                    ai_data = json.loads(cached_ai)
                    # Check timestamp if available
                    if "timestamp" in ai_data:
                        ai_timestamp = datetime.fromisoformat(ai_data["timestamp"].replace("Z", "+00:00"))
                        age_minutes = (datetime.utcnow() - ai_timestamp.replace(tzinfo=None)).total_seconds() / 60
                        if age_minutes > 5:
                            should_generate = True
                    else:
                        ai_insight = ai_data
                except Exception:
                    ai_insight = json.loads(cached_ai)
            else:
                should_generate = True
            
            # Auto-generate AI insight if needed
            if should_generate and market_overview:
                try:
                    # Prepare market data for AI insight
                    market_data_for_ai = {
                        "market": {
                            "total_market_cap": market_overview.get("total_market_cap", 0),
                            "total_volume_24h": market_overview.get("total_volume_24h", 0),
                            "market_cap_change_24h": market_overview.get("market_cap_change_24h", 0),
                            "btc_dominance": dominance_data.get("btc_dominance", 0) if dominance_data else market_overview.get("btc_dominance", 0),
                            "fear_greed": feargreed_data.get("value", 50) if feargreed_data else 50,
                            "volatility_index": volatility_data.get("volatility_index", 0.5) if volatility_data else 0.5,
                            "trend_score": 50,  # Default, can be calculated
                        }
                    }
                    
                    # Call AI service to generate insight
                    ai_service_url = settings.AI_SERVICE_URL
                    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                        ai_response = await client.post(
                            f"{ai_service_url}/ai/market",
                            json=market_data_for_ai,
                            headers={"Authorization": auth_header} if auth_header else {}
                        )
                        if ai_response.status_code == 200:
                            ai_insight = ai_response.json()
                            # Cache the new insight
                            ai_insight["timestamp"] = datetime.utcnow().isoformat() + "Z"
                            redis_client.setex(ai_cache_key, 300, json.dumps(ai_insight))  # 5 minutes
                            logger.info("AI Insight auto-generated successfully")
                except Exception as e:
                    logger.warning(f"Failed to auto-generate AI insight: {e}")
                    # Fallback to cached insight if available
                    if cached_ai:
                        try:
                            ai_insight = json.loads(cached_ai)
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Error processing AI insight: {e}")
    
    # Phase 1.1: Real-time Data Integration
    websocket_status = "disconnected"  # Default
    try:
        # Check WebSocket service health
        realtime_service_url = settings.REALTIME_SERVICE_URL
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0)) as client:
            health_response = await client.get(f"{realtime_service_url}/health")
            if health_response.status_code == 200:
                websocket_status = "connected"
    except Exception:
        pass  # WebSocket service may not be available
    
    # Build response with optimized fields
    response = {
        "market": {
            "overview": market_overview,
            "topGainers": top_gainers,
            "topLosers": top_losers,
            "dominance": dominance_data,
            "fearGreed": feargreed_data,
            "volatility": volatility_data,
        },
        "portfolio": portfolio_data,
        "watchlist": watchlist_data,
        "aiInsight": ai_insight,
        # Phase 1.1: Portfolio Advanced Metrics
        "portfolioMetrics": {
            "sharpeRatio": sharpe_ratio_data,
            "alphaBeta": alpha_beta_data,
        } if auth_header else None,
        "quickStats": {
            "activeCoins": market_overview.get("active_cryptocurrencies", 0) if market_overview else 0,
            "btcDominance": dominance_data.get("btc_dominance", 0) if dominance_data else (market_overview.get("btc_dominance", 0) if market_overview else 0),
            "marketTrend": "bullish" if (market_overview.get("market_cap_change_24h", 0) > 0 if market_overview else False) else "bearish",
        },
        # Phase 1.1: Real-time Data Integration
        "realtime": {
            "websocketStatus": websocket_status,
            "lastUpdate": datetime.utcnow().isoformat() + "Z",
            "dataFreshness": "fresh",  # Can be "fresh", "stale", "cached"
        },
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "cacheExpiry": (datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z",
    }
    
    # Cache response using multi-layer cache (L1 + L2)
    try:
        cache_manager.set(user_cache_key, response, ttl_l1=30, ttl_l2=60)
    except Exception as e:
        logger.warning(f"Failed to cache response: {e}")
    
    return response


# Portfolio Dashboard API route - Enhanced with Phase 1.1 improvements
@router.get("/portfolio/dashboard")
async def get_portfolio_dashboard(request: Request = None):
    """
    Get aggregated portfolio dashboard data.
    Returns all data needed for the portfolio page in a single response.
    Uses batch request internally for optimal performance.
    
    Phase 1.1 Enhancements:
    - AI Insight auto-generation (if cache miss or stale > 5 minutes)
    - Multi-layer caching (L1/L2) with user-specific keys
    - Real-time Data Integration (last update timestamp, data freshness)
    - Error Handling & Fallbacks (graceful degradation)
    - Response Optimization (field selection, compression-ready)
    """
    from datetime import datetime, timedelta
    from shared.cache_manager import get_cache_manager
    from shared.redis_client import get_redis
    import json
    import logging
    import httpx
    
    logger = logging.getLogger(__name__)
    cache_manager = get_cache_manager()
    redis_client = get_redis()
    
    if not request:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # User-specific cache key
    user_cache_key = f"portfolio:dashboard:{hash(auth_header) % 10000}"
    
    # Try to get from multi-layer cache first (L1 -> L2)
    cached_data = cache_manager.get(user_cache_key, ttl_l1=30, ttl_l2=60)
    if cached_data:
        # Check if AI insight is stale (> 5 minutes)
        ai_insight_timestamp = cached_data.get("aiInsight", {}).get("timestamp")
        if ai_insight_timestamp:
            try:
                ai_insight_time = datetime.fromisoformat(ai_insight_timestamp.replace("Z", "+00:00"))
                age_minutes = (datetime.utcnow() - ai_insight_time.replace(tzinfo=None)).total_seconds() / 60
                if age_minutes > 5:
                    # AI insight is stale, will regenerate below
                    logger.debug(f"AI insight stale ({age_minutes:.1f} minutes), will regenerate")
                else:
                    # Return cached data (fresh)
                    return cached_data
            except Exception:
                # If timestamp parsing fails, return cached data anyway
                return cached_data
        else:
            # No AI insight in cache, return cached data but will add AI insight below
            pass
    
    # Build batch request for all portfolio page data
    batch_requests = [
        BatchRequestItem(method="GET", path="/portfolio", id="portfolio"),
        BatchRequestItem(method="GET", path="/portfolio/performance", params={"timeframe": "1D"}, id="performance"),
        BatchRequestItem(method="GET", path="/portfolio/transactions", params={"limit": 50}, id="transactions"),
        BatchRequestItem(method="GET", path="/portfolio/wallets", id="wallets"),
        BatchRequestItem(method="GET", path="/portfolio/analytics/sharpe-ratio", id="sharpeRatio"),
        BatchRequestItem(method="GET", path="/portfolio/analytics/alpha-beta", id="alphaBeta"),
        BatchRequestItem(method="GET", path="/portfolio/tax/realized-unrealized", id="realizedUnrealized"),
        BatchRequestItem(method="GET", path="/portfolio/rebalancing/suggestions", id="rebalancingSuggestions"),
        # Phase 1.4: Advanced metrics integration
        BatchRequestItem(method="GET", path="/portfolio/dca/plans", params={"is_active": True}, id="dcaPlans"),
        BatchRequestItem(method="GET", path="/portfolio/performance", params={"timeframe": "30D"}, id="performance30D"),
        BatchRequestItem(method="GET", path="/portfolio/performance", params={"timeframe": "90D"}, id="performance90D"),
        BatchRequestItem(method="GET", path="/portfolio/performance", params={"timeframe": "1Y"}, id="performance1Y"),
    ]
    
    # Execute batch request with error handling
    batch = BatchRequest(requests=batch_requests)
    try:
        batch_result = await batch_request(batch, request=request)
    except Exception as e:
        logger.error(f"Batch request failed: {e}")
        # Fallback: Try to return cached data even if stale
        cached_data = cache_manager.get(user_cache_key, ttl_l1=0, ttl_l2=0)  # Accept stale data
        if cached_data:
            logger.warning(f"Returning stale cache due to batch request failure")
            return cached_data
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    # Process results with graceful degradation
    results_dict = {r["id"]: r for r in batch_result["results"]}
    
    # Extract and process data (with fallbacks)
    def safe_get(result_key: str, default: Any = None):
        """Safely get result data with fallback."""
        result = results_dict.get(result_key, {})
        if result.get("status") == 200:
            return result.get("data", default)
        logger.warning(f"Failed to get {result_key}: {result.get('error', 'Unknown error')}")
        return default
    
    portfolio_data = safe_get("portfolio", {})
    performance_data = safe_get("performance", {})
    transactions_data = safe_get("transactions", {}).get("transactions", []) if safe_get("transactions", {}) else []
    wallets_data = safe_get("wallets", [])
    sharpe_ratio_data = safe_get("sharpeRatio", {})
    alpha_beta_data = safe_get("alphaBeta", {})
    realized_unrealized_data = safe_get("realizedUnrealized", {})
    rebalancing_suggestions_data = safe_get("rebalancingSuggestions", {})
    # Phase 1.4: Advanced metrics integration
    dca_plans_data = safe_get("dcaPlans", [])
    performance_30d = safe_get("performance30D", {})
    performance_90d = safe_get("performance90D", {})
    performance_1y = safe_get("performance1Y", {})
    
    # Phase 1.1: AI Insight auto-generation
    ai_insight = None
    ai_insight_cache_key = f"ai_insights:portfolio:{hash(auth_header) % 10000}"
    
    # Check if we need to generate AI insight
    should_generate_ai = True
    try:
        cached_ai = cache_manager.get(ai_insight_cache_key, ttl_l1=300, ttl_l2=300)
        if cached_ai:
            ai_insight_timestamp = cached_ai.get("timestamp")
            if ai_insight_timestamp:
                try:
                    ai_insight_time = datetime.fromisoformat(ai_insight_timestamp.replace("Z", "+00:00"))
                    age_minutes = (datetime.utcnow() - ai_insight_time.replace(tzinfo=None)).total_seconds() / 60
                    if age_minutes <= 5:
                        ai_insight = cached_ai
                        should_generate_ai = False
                except Exception:
                    pass
    except Exception:
        pass
    
    # Generate AI insight if needed
    if should_generate_ai and portfolio_data:
        try:
            # Prepare portfolio data for AI
            portfolio_for_ai = {
                "portfolio": {
                    "total_value": portfolio_data.get("total_value", 0),
                    "total_profit_loss": portfolio_data.get("total_profit_loss", 0),
                    "total_profit_loss_percent": portfolio_data.get("total_profit_loss_percent", 0),
                    "items": portfolio_data.get("items", []),
                    "risk_score": portfolio_data.get("risk_score", 50),
                    "diversification_score": portfolio_data.get("diversification_score", 0.5),
                    "performance_score": portfolio_data.get("performance_score", 50),
                }
            }
            
            # Call AI service
            ai_service_url = settings.AI_SERVICE_URL
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                ai_response = await client.post(
                    f"{ai_service_url}/ai/portfolio",
                    json=portfolio_for_ai,
                    headers={"Authorization": auth_header} if auth_header else {}
                )
                if ai_response.status_code == 200:
                    ai_insight = ai_response.json()
                    ai_insight["timestamp"] = datetime.utcnow().isoformat() + "Z"
                    
                    # Cache AI insight (user-specific, 5 minutes TTL)
                    cache_manager.set(ai_insight_cache_key, ai_insight, ttl_l1=300, ttl_l2=300)
                    logger.info("Portfolio AI insight generated and cached")
                else:
                    logger.warning(f"AI service returned {ai_response.status_code}: {ai_response.text}")
        except Exception as e:
            logger.warning(f"Failed to generate AI insight: {e}")
            # Continue without AI insight (graceful degradation)
    
    # Phase 1.1: Real-time Data Integration
    websocket_status = "connected"  # Default - would check actual WebSocket status
    try:
        # Check WebSocket service status (if available)
        # This is a placeholder - actual implementation would check WebSocket connection
        pass
    except Exception:
        websocket_status = "disconnected"
    
    # Build response with optimized fields
    response = {
        "portfolio": portfolio_data,
        "performance": performance_data,
        "transactions": transactions_data,
        "wallets": wallets_data,
        "analytics": {
            "sharpeRatio": sharpe_ratio_data,
            "alphaBeta": alpha_beta_data,
            "realizedUnrealized": realized_unrealized_data,
            "rebalancingSuggestions": rebalancing_suggestions_data,
        },
        # Phase 1.4: Advanced metrics integration
        "dcaPlans": dca_plans_data,
        "historicalPerformance": {
            "30D": performance_30d,
            "90D": performance_90d,
            "1Y": performance_1y,
        },
        # Phase 1.1: AI Insight auto-generation
        "aiInsight": ai_insight,
        # Phase 1.1: Real-time Data Integration
        "realtime": {
            "websocketStatus": websocket_status,
            "lastUpdate": datetime.utcnow().isoformat() + "Z",
            "dataFreshness": "fresh",  # Can be "fresh", "stale", "cached"
        },
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "cacheExpiry": (datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z",
    }
    
    # Cache response using multi-layer cache (L1 + L2)
    try:
        cache_manager.set(user_cache_key, response, ttl_l1=30, ttl_l2=60)
    except Exception as e:
        logger.warning(f"Failed to cache portfolio dashboard: {e}")
    
    return response


# Notification API routes
@router.post("/notifications/register-token")
async def register_notification_token(request: Request):
    """Proxy to Notification Service - POST /notifications/register-token"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    return await proxy_request(
        settings.NOTIFICATION_SERVICE_URL,
        "/notifications/register-token",
        method="POST",
        request=request,
        json=body
    )


@router.get("/notifications/history")
async def get_notification_history(limit: int = 50, request: Request = None):
    """Proxy to Notification Service - GET /notifications/history"""
    return await proxy_request(
        settings.NOTIFICATION_SERVICE_URL,
        "/notifications/history",
        request=request,
        params={"limit": limit}
    )


# Phase 1.4: Cache Metrics Endpoints
@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    Returns cache hit/miss rates, sizes, and detailed metrics.
    """
    from shared.cache_manager import get_cache_manager
    
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()
    
    return {
        "status": "ok",
        "cache": stats,
    }


@router.post("/cache/invalidate")
async def invalidate_cache(pattern: str = None, key: str = None):
    """
    Invalidate cache entries.
    
    Args:
        pattern: Pattern to match (e.g., "market:dashboard:*")
        key: Specific key to invalidate
    
    Returns:
        Success message
    """
    from shared.cache_manager import get_cache_manager
    
    cache_manager = get_cache_manager()
    
    if pattern:
        cache_manager.invalidate_pattern(pattern)
        return {"status": "ok", "message": f"Cache pattern '{pattern}' invalidated"}
    elif key:
        cache_manager.invalidate(key)
        return {"status": "ok", "message": f"Cache key '{key}' invalidated"}
    else:
        raise HTTPException(status_code=400, detail="Either 'pattern' or 'key' must be provided")


@router.post("/batch")
async def batch_request(batch: BatchRequest, request: Request = None):
    """
    Execute multiple API requests in parallel.
    
    Request body:
    {
        "requests": [
            {
                "method": "GET",
                "path": "/market/overview",
                "params": {},
                "id": "market_overview"
            },
            {
                "method": "GET",
                "path": "/market/heatmap",
                "params": {"limit": 100},
                "id": "heatmap"
            }
        ]
    }
    
    Response:
    {
        "results": [
            {
                "id": "market_overview",
                "status": 200,
                "data": {...}
            },
            {
                "id": "heatmap",
                "status": 200,
                "data": {...}
            }
        ]
    }
    """
    if not batch.requests:
        raise HTTPException(status_code=400, detail="No requests provided")
    
    if len(batch.requests) > 20:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 20 requests per batch")
    
    # Get auth header
    auth_header = None
    if request:
        auth_header = request.headers.get("Authorization")
    
    # Determine service URL for each request
    def get_service_url(path: str) -> str:
        """Determine which service to route to based on path."""
        if path.startswith("/market"):
            return settings.MARKET_SERVICE_URL
        elif path.startswith("/portfolio"):
            return settings.PORTFOLIO_SERVICE_URL
        elif path.startswith("/coin") or path.startswith("/analytics"):
            return settings.ANALYTICS_SERVICE_URL
        elif path.startswith("/alerts"):
            return settings.ALERT_SERVICE_URL
        elif path.startswith("/watchlist"):
            return settings.WATCHLIST_SERVICE_URL
        elif path.startswith("/realtime"):
            return settings.REALTIME_SERVICE_URL
        elif path.startswith("/notifications"):
            return settings.NOTIFICATION_SERVICE_URL
        elif path.startswith("/ai"):
            return settings.AI_SERVICE_URL
        else:
            return settings.MARKET_SERVICE_URL  # Default
    
    # Execute all requests in parallel
    async def execute_request(req: BatchRequestItem) -> Dict[str, Any]:
        """Execute a single request."""
        try:
            service_url = get_service_url(req.path)
            url = f"{service_url}{req.path}"
            
            headers = {}
            if auth_header:
                headers["Authorization"] = auth_header
            
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                if req.method == "GET":
                    response = await client.get(url, params=req.params, headers=headers)
                elif req.method == "POST":
                    response = await client.post(url, json=req.body, params=req.params, headers=headers)
                elif req.method == "PUT":
                    response = await client.put(url, json=req.body, params=req.params, headers=headers)
                elif req.method == "DELETE":
                    response = await client.delete(url, params=req.params, headers=headers)
                else:
                    return {
                        "id": req.id,
                        "status": 405,
                        "error": "Method not allowed"
                    }
                
                response.raise_for_status()
                return {
                    "id": req.id,
                    "status": response.status_code,
                    "data": response.json()
                }
        except httpx.HTTPStatusError as e:
            error_detail = "Service error"
            try:
                if e.response is not None:
                    error_data = e.response.json()
                    error_detail = error_data.get("detail", error_data.get("message", str(e)))
            except:
                error_detail = str(e)
            
            return {
                "id": req.id,
                "status": e.response.status_code if e.response else 503,
                "error": error_detail
            }
        except Exception as e:
            return {
                "id": req.id,
                "status": 500,
                "error": str(e)
            }
    
    # Execute all requests in parallel
    results = await asyncio.gather(*[execute_request(req) for req in batch.requests])
    
    return {
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if r.get("status", 0) < 400),
        "failed": sum(1 for r in results if r.get("status", 0) >= 400)
    }


# Phase 1.2: Cache Management Endpoints
@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    Phase 1.2: Cache Metrics
    """
    from shared.cache_manager import get_cache_manager
    
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()
    
    return {
        "status": "ok",
        "cache": stats
    }


@router.post("/cache/invalidate")
async def invalidate_cache(pattern: str = None, key: str = None):
    """
    Invalidate cache entries.
    Phase 1.2: Cache Invalidation
    
    Args:
        pattern: Pattern to match (e.g., "home:dashboard:*")
        key: Specific cache key to invalidate
    """
    from shared.cache_manager import get_cache_manager
    
    if not pattern and not key:
        raise HTTPException(status_code=400, detail="Either 'pattern' or 'key' must be provided")
    
    cache_manager = get_cache_manager()
    
    if key:
        cache_manager.invalidate(key)
        return {"status": "ok", "message": f"Cache key '{key}' invalidated"}
    elif pattern:
        cache_manager.invalidate_pattern(pattern)
        return {"status": "ok", "message": f"Cache pattern '{pattern}' invalidated"}
