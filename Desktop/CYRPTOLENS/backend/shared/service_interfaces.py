"""
Service interfaces for dependency injection and testability.
Provides abstract base classes for all services.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
from uuid import UUID


class IAuthService(ABC):
    """Interface for authentication service."""
    
    @abstractmethod
    def register_user(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: str,
        country: str,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new user."""
        pass
    
    @abstractmethod
    def login_user(
        self,
        db: Session,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """Authenticate user and return token."""
        pass
    
    @abstractmethod
    def reset_password(
        self,
        db: Session,
        email: str
    ) -> Dict[str, Any]:
        """Initiate password reset."""
        pass
    
    @abstractmethod
    def confirm_password_reset(
        self,
        db: Session,
        email: str,
        reset_token: str,
        new_password: str
    ) -> Dict[str, Any]:
        """Confirm password reset with token."""
        pass


class IMarketDataService(ABC):
    """Interface for market data service."""
    
    @abstractmethod
    async def get_market_overview(self, db: Session) -> Dict[str, Any]:
        """Get market overview data."""
        pass
    
    @abstractmethod
    async def get_heatmap(self, db: Session, limit: int = 100) -> Dict[str, Any]:
        """Get market heatmap data."""
        pass
    
    @abstractmethod
    async def get_dominance(self, db: Session) -> Dict[str, Any]:
        """Get market dominance data."""
        pass
    
    @abstractmethod
    async def get_fear_greed(self) -> Dict[str, Any]:
        """Get Fear & Greed Index."""
        pass
    
    @abstractmethod
    async def get_volatility(self, db: Session) -> Dict[str, Any]:
        """Get market volatility data."""
        pass


class IPortfolioService(ABC):
    """Interface for portfolio service."""
    
    @abstractmethod
    def get_user_portfolio(
        self,
        db: Session,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get user portfolio."""
        pass
    
    @abstractmethod
    def add_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        amount: Decimal,
        buy_price: Decimal
    ) -> Dict[str, Any]:
        """Add portfolio item."""
        pass
    
    @abstractmethod
    def update_portfolio_item(
        self,
        db: Session,
        item_id: UUID,
        amount: Optional[Decimal] = None,
        buy_price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Update portfolio item."""
        pass
    
    @abstractmethod
    def remove_portfolio_item(
        self,
        db: Session,
        item_id: UUID
    ) -> Dict[str, Any]:
        """Remove portfolio item."""
        pass


class IAlertService(ABC):
    """Interface for alert service."""
    
    @abstractmethod
    def get_user_alerts(
        self,
        db: Session,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get user alerts."""
        pass
    
    @abstractmethod
    def create_alert(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        alert_type: str,
        condition: str,
        value: Decimal
    ) -> Dict[str, Any]:
        """Create alert."""
        pass
    
    @abstractmethod
    def update_alert(
        self,
        db: Session,
        alert_id: UUID,
        enabled: Optional[bool] = None,
        value: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Update alert."""
        pass
    
    @abstractmethod
    def delete_alert(
        self,
        db: Session,
        alert_id: UUID
    ) -> Dict[str, Any]:
        """Delete alert."""
        pass


class IWatchlistService(ABC):
    """Interface for watchlist service."""
    
    @abstractmethod
    def get_user_watchlist(
        self,
        db: Session,
        user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get user watchlist."""
        pass
    
    @abstractmethod
    def add_to_watchlist(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str
    ) -> Dict[str, Any]:
        """Add coin to watchlist."""
        pass
    
    @abstractmethod
    def remove_from_watchlist(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str
    ) -> Dict[str, Any]:
        """Remove coin from watchlist."""
        pass

