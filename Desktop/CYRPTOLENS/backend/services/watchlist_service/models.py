"""
Pydantic models for Watchlist Service.
"""
from pydantic import BaseModel
from typing import List
from datetime import datetime
from uuid import UUID


class WatchlistItemResponse(BaseModel):
    """Response model for a watchlist item."""
    id: UUID
    coin_symbol: str
    created_at: datetime


class WatchlistResponse(BaseModel):
    """Response model for user's watchlist."""
    items: List[WatchlistItemResponse]
    total_count: int


class AddWatchlistItemRequest(BaseModel):
    """Request model for adding a coin to watchlist."""
    coin_symbol: str


class RemoveWatchlistItemResponse(BaseModel):
    """Response model for removing a watchlist item."""
    success: bool
    message: str

