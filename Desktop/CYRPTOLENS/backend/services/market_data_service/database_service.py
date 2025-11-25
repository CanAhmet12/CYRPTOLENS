"""
Database service for Market Data Service.
Handles market_cache table operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from shared.database import get_db
from shared.models import MarketCache


class MarketDatabaseService:
    """Service for database operations on market_cache table."""
    
    def upsert_market_data(
        self,
        db: Session,
        symbol: str,
        price: Decimal,
        volume24: Optional[Decimal] = None,
        dominance: Optional[Decimal] = None,
        market_cap: Optional[Decimal] = None,
        price_change_24h: Optional[Decimal] = None
    ) -> MarketCache:
        """Insert or update market data for a coin."""
        # Check if record exists
        stmt = select(MarketCache).where(MarketCache.symbol == symbol)
        result = db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing record
            existing.price = price
            if volume24 is not None:
                existing.volume24 = volume24
            if dominance is not None:
                existing.dominance = dominance
            if market_cap is not None:
                existing.market_cap = market_cap
            if price_change_24h is not None:
                existing.price_change_24h = price_change_24h
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new record
            new_record = MarketCache(
                symbol=symbol,
                price=price,
                volume24=volume24,
                dominance=dominance,
                market_cap=market_cap,
                price_change_24h=price_change_24h
            )
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            return new_record
    
    def get_market_data(self, db: Session, symbol: str) -> Optional[MarketCache]:
        """Get market data for a specific coin."""
        stmt = select(MarketCache).where(MarketCache.symbol == symbol)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_all_market_data(self, db: Session, limit: int = 100) -> List[MarketCache]:
        """Get all market data, ordered by updated_at."""
        stmt = select(MarketCache).order_by(MarketCache.updated_at.desc()).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def bulk_upsert_market_data(
        self,
        db: Session,
        market_data_list: List[dict]
    ) -> List[MarketCache]:
        """Bulk insert/update market data for multiple coins."""
        results = []
        for data in market_data_list:
            result = self.upsert_market_data(
                db=db,
                symbol=data["symbol"],
                price=data["price"],
                volume24=data.get("volume24"),
                dominance=data.get("dominance"),
                market_cap=data.get("market_cap"),
                price_change_24h=data.get("price_change_24h")
            )
            results.append(result)
        return results

