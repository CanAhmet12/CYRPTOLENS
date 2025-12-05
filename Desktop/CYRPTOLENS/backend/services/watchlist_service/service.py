"""
Main business logic service for Watchlist.
"""
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from .database_service import WatchlistDatabaseService
from .models import (
    WatchlistResponse,
    WatchlistItemResponse,
    AddWatchlistItemRequest,
    RemoveWatchlistItemResponse,
)
from datetime import datetime


class WatchlistService:
    """Main service for watchlist operations."""
    
    def __init__(self):
        self.db_service = WatchlistDatabaseService()
    
    def get_watchlist(
        self, db: Session, user_id: UUID
    ) -> WatchlistResponse:
        """Get user's complete watchlist."""
        items_data = self.db_service.get_user_watchlist(db, user_id)
        
        items = [
            WatchlistItemResponse(
                id=item["id"],
                coin_symbol=item["coin_symbol"],
                created_at=item["created_at"]
            )
            for item in items_data
        ]
        
        return WatchlistResponse(
            items=items,
            total_count=len(items)
        )
    
    def add_item(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> WatchlistItemResponse:
        """Add a coin to watchlist."""
        item_data = self.db_service.add_watchlist_item(
            db, user_id, coin_symbol
        )
        
        return WatchlistItemResponse(
            id=item_data["id"],
            coin_symbol=item_data["coin_symbol"],
            created_at=item_data["created_at"] or datetime.utcnow()
        )
    
    def remove_item(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> RemoveWatchlistItemResponse:
        """Remove a coin from watchlist."""
        success = self.db_service.remove_watchlist_item(
            db, user_id, coin_symbol
        )
        
        return RemoveWatchlistItemResponse(
            success=success,
            message="Item removed from watchlist" if success else "Item not found"
        )
    
    def is_in_watchlist(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> bool:
        """Check if coin is in watchlist."""
        return self.db_service.is_in_watchlist(db, user_id, coin_symbol)

