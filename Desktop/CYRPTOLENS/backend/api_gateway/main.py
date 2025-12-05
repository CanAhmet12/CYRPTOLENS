"""
API Gateway main application.
Routes requests to appropriate microservices.
"""
# Standard library imports
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Local application imports
from shared.config import settings
from shared.sentry_init import init_sentry
from shared.background_tasks import get_background_task_manager
from shared.api_versioning import CURRENT_API_VERSION
from .routes import router
from .middleware import APIVersioningMiddleware

# Initialize Sentry
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Phase 1.3: Background Tasks Integration
    """
    # Startup: Start background tasks
    background_manager = get_background_task_manager()
    await background_manager.start()
    
    yield
    
    # Shutdown: Stop background tasks
    await background_manager.stop()


app = FastAPI(
    title="CryptoLens API Gateway",
    version=settings.APP_VERSION,
    description="""
    CryptoLens API Gateway - Microservices Architecture
    
    This API Gateway routes requests to appropriate microservices and provides:
    
    * **Market Data**: Real-time and historical cryptocurrency market data
    * **Portfolio Management**: User portfolio tracking and analytics
    * **AI Insights**: AI-powered market and portfolio insights
    * **Authentication**: User registration, login, and password management
    * **Watchlist**: Track favorite cryptocurrencies
    * **Alerts**: Price and market change alerts
    
    ## Authentication
    
    Most endpoints require authentication via JWT token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```
    
    ## Rate Limiting
    
    API requests are rate-limited. Check response headers for rate limit information.
    
    ## Error Responses
    
    All errors follow a standardized format:
    ```json
    {
        "error": true,
        "error_code": "ERROR_CODE",
        "message": "Human-readable error message",
        "detail": "Additional error details"
    }
    ```
    """,
    lifespan=lifespan,  # Phase 1.3: Background Tasks Integration
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "Market", "description": "Market data and statistics endpoints"},
        {"name": "Portfolio", "description": "Portfolio management endpoints"},
        {"name": "Coin", "description": "Individual coin data and analytics"},
        {"name": "Authentication", "description": "User authentication and authorization"},
        {"name": "AI Insights", "description": "AI-powered market and portfolio insights"},
        {"name": "Watchlist", "description": "Watchlist management endpoints"},
        {"name": "Alerts", "description": "Price and market alerts"},
        {"name": "Health", "description": "Health check and system status"},
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compression middleware - GZip compression for responses > 1KB
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Compress responses larger than 1KB
)

# API Versioning middleware - Must be after compression
app.add_middleware(APIVersioningMiddleware)

# Include routes with versioning support
# Current version (v1) - default
app.include_router(router, prefix="/api/v1", tags=["v1"])
# Legacy support - redirect /api to /api/v1
app.include_router(router, prefix="/api", tags=["v1"])


@app.get(
    "/",
    response_model=dict,
    summary="Root endpoint",
    description="API Gateway root endpoint with service information.",
    tags=["Health"],
)
async def root():
    """
    Health check endpoint.
    
    Returns:
        dict: Service status and version information
    """
    return {
        "status": "ok",
        "service": "api_gateway",
        "version": settings.APP_VERSION,
        "api_version": CURRENT_API_VERSION.value,
        "endpoints": {
            "v1": "/api/v1",
            "legacy": "/api (redirects to v1)",
        }
    }


@app.get(
    "/health",
    response_model=dict,
    summary="Health check",
    description="Check API Gateway health status.",
    tags=["Health"],
)
async def health():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy"}
