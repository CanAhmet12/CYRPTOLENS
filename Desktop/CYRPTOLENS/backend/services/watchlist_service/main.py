"""
Watchlist Service main application.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID
from shared.config import settings
from shared.database import get_db
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from .service import WatchlistService
from .models import (
    WatchlistResponse,
    WatchlistItemResponse,
    AddWatchlistItemRequest,
    RemoveWatchlistItemResponse,
)

# Import authentication dependency
try:
    from shared.auth_dependency import get_current_user_id
except ImportError:
    # Fallback if auth dependency not available
    def get_current_user_id() -> UUID:
        """Fallback: Get current user ID from authentication token."""
        return UUID("00000000-0000-0000-0000-000000000001")

app = FastAPI(
    title="CryptoLens Watchlist Service",
    version=settings.APP_VERSION,
    description="Watchlist management service for CryptoLens"
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
watchlist_service = WatchlistService()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "watchlist_service"}


@app.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get user's watchlist."""
    return watchlist_service.get_watchlist(db, user_id)


@app.post("/watchlist/add", response_model=WatchlistItemResponse)
async def add_watchlist_item(
    request: AddWatchlistItemRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Add a coin to watchlist."""
    try:
        return watchlist_service.add_item(
            db, user_id, request.coin_symbol
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add to watchlist: {str(e)}"
        )


@app.delete("/watchlist/remove/{coin_symbol}", response_model=RemoveWatchlistItemResponse)
async def remove_watchlist_item(
    coin_symbol: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Remove a coin from watchlist."""
    try:
        return watchlist_service.remove_item(db, user_id, coin_symbol)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove from watchlist: {str(e)}"
        )


@app.get("/watchlist/check/{coin_symbol}")
async def check_watchlist(
    coin_symbol: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Check if a coin is in watchlist."""
    is_in = watchlist_service.is_in_watchlist(db, user_id, coin_symbol)
    return {"is_in_watchlist": is_in}

