"""
Database service for Portfolio Service.
Handles portfolio table operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from shared.models import Portfolio, MarketCache


class PortfolioDatabaseService:
    """Service for database operations on portfolio table."""
    
    def get_user_portfolio(self, db: Session, user_id: UUID) -> List[Portfolio]:
        """Get all portfolio items for a user."""
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def get_portfolio_item(
        self, db: Session, user_id: UUID, item_id: UUID
    ) -> Optional[Portfolio]:
        """Get a specific portfolio item."""
        stmt = select(Portfolio).where(
            Portfolio.id == item_id,
            Portfolio.user_id == user_id
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_portfolio_item_by_symbol(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> Optional[Portfolio]:
        """Get portfolio item by coin symbol."""
        stmt = select(Portfolio).where(
            Portfolio.user_id == user_id,
            Portfolio.coin_symbol == coin_symbol.upper()
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def add_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        amount: Decimal,
        buy_price: Decimal
    ) -> Portfolio:
        """Add a new portfolio item."""
        # Check if item already exists for this user and coin
        existing = self.get_portfolio_item_by_symbol(db, user_id, coin_symbol)
        if existing:
            # Update existing item
            existing.amount = amount
            existing.buy_price = buy_price
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new item
        new_item = Portfolio(
            user_id=user_id,
            coin_symbol=coin_symbol.upper(),
            amount=amount,
            buy_price=buy_price
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item
    
    def update_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        item_id: UUID,
        amount: Optional[Decimal] = None,
        buy_price: Optional[Decimal] = None
    ) -> Optional[Portfolio]:
        """Update a portfolio item."""
        item = self.get_portfolio_item(db, user_id, item_id)
        if not item:
            return None
        
        if amount is not None:
            item.amount = amount
        if buy_price is not None:
            item.buy_price = buy_price
        
        db.commit()
        db.refresh(item)
        return item
    
    def delete_portfolio_item(
        self, db: Session, user_id: UUID, item_id: UUID
    ) -> bool:
        """Delete a portfolio item."""
        item = self.get_portfolio_item(db, user_id, item_id)
        if not item:
            return False
        
        db.delete(item)
        db.commit()
        return True
    
    def get_current_price(self, db: Session, coin_symbol: str) -> Optional[Decimal]:
        """Get current price for a coin from market_cache."""
        stmt = select(MarketCache).where(
            MarketCache.symbol == coin_symbol.upper()
        )
        result = db.execute(stmt)
        market_data = result.scalar_one_or_none()
        if market_data:
            return market_data.price
        return None

