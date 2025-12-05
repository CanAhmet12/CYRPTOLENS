"""
Database service for Watchlist operations.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from shared.models import User, MarketCache


class WatchlistItem:
    """Watchlist item model (not using ORM for simplicity)."""
    def __init__(self, id: UUID, coin_symbol: str, created_at):
        self.id = id
        self.coin_symbol = coin_symbol
        self.created_at = created_at


class WatchlistDatabaseService:
    """Handles database operations for watchlist."""
    
    def get_user_watchlist(self, db: Session, user_id: UUID) -> List[dict]:
        """Get all watchlist items for a user."""
        # Using raw SQL for simplicity (watchlist table not in ORM models yet)
        result = db.execute(
            """
            SELECT id, coin_symbol, created_at
            FROM watchlist
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            """,
            {"user_id": str(user_id)}
        )
        items = []
        for row in result:
            items.append({
                "id": row[0],
                "coin_symbol": row[1],
                "created_at": row[2]
            })
        return items
    
    def add_watchlist_item(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> dict:
        """Add a coin to user's watchlist."""
        # Check if already exists
        existing = db.execute(
            """
            SELECT id FROM watchlist
            WHERE user_id = :user_id AND coin_symbol = :coin_symbol
            """,
            {"user_id": str(user_id), "coin_symbol": coin_symbol.upper()}
        ).first()
        
        if existing:
            return {
                "id": existing[0],
                "coin_symbol": coin_symbol.upper(),
                "created_at": None  # Will be fetched
            }
        
        # Insert new item
        result = db.execute(
            """
            INSERT INTO watchlist (user_id, coin_symbol)
            VALUES (:user_id, :coin_symbol)
            RETURNING id, coin_symbol, created_at
            """,
            {"user_id": str(user_id), "coin_symbol": coin_symbol.upper()}
        )
        row = result.first()
        db.commit()
        
        return {
            "id": row[0],
            "coin_symbol": row[1],
            "created_at": row[2]
        }
    
    def remove_watchlist_item(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> bool:
        """Remove a coin from user's watchlist."""
        result = db.execute(
            """
            DELETE FROM watchlist
            WHERE user_id = :user_id AND coin_symbol = :coin_symbol
            """,
            {"user_id": str(user_id), "coin_symbol": coin_symbol.upper()}
        )
        db.commit()
        return result.rowcount > 0
    
    def is_in_watchlist(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> bool:
        """Check if a coin is in user's watchlist."""
        result = db.execute(
            """
            SELECT id FROM watchlist
            WHERE user_id = :user_id AND coin_symbol = :coin_symbol
            """,
            {"user_id": str(user_id), "coin_symbol": coin_symbol.upper()}
        ).first()
        return result is not None

