"""
Service factory for dependency injection.
Provides centralized service instantiation.
"""
from typing import Optional
from sqlalchemy.orm import Session
from .service_interfaces import (
    IAuthService,
    IMarketDataService,
    IPortfolioService,
    IAlertService,
    IWatchlistService,
)


class ServiceFactory:
    """Factory for creating service instances."""
    
    # Service instances cache
    _auth_service: Optional[IAuthService] = None
    _market_data_service: Optional[IMarketDataService] = None
    _portfolio_service: Optional[IPortfolioService] = None
    _alert_service: Optional[IAlertService] = None
    _watchlist_service: Optional[IWatchlistService] = None
    
    @classmethod
    def get_auth_service(cls) -> IAuthService:
        """Get or create auth service instance."""
        if cls._auth_service is None:
            from services.auth_service.service import AuthService
            cls._auth_service = AuthService()
        return cls._auth_service
    
    @classmethod
    def get_market_data_service(cls) -> IMarketDataService:
        """Get or create market data service instance."""
        if cls._market_data_service is None:
            from services.market_data_service.service import MarketDataService
            cls._market_data_service = MarketDataService()
        return cls._market_data_service
    
    @classmethod
    def get_portfolio_service(cls) -> IPortfolioService:
        """Get or create portfolio service instance."""
        if cls._portfolio_service is None:
            from services.portfolio_service.service import PortfolioService
            cls._portfolio_service = PortfolioService()
        return cls._portfolio_service
    
    @classmethod
    def get_alert_service(cls) -> IAlertService:
        """Get or create alert service instance."""
        if cls._alert_service is None:
            from services.alert_service.service import AlertService
            cls._alert_service = AlertService()
        return cls._alert_service
    
    @classmethod
    def get_watchlist_service(cls) -> IWatchlistService:
        """Get or create watchlist service instance."""
        if cls._watchlist_service is None:
            from services.watchlist_service.service import WatchlistService
            cls._watchlist_service = WatchlistService()
        return cls._watchlist_service
    
    @classmethod
    def reset(cls):
        """Reset all service instances (useful for testing)."""
        cls._auth_service = None
        cls._market_data_service = None
        cls._portfolio_service = None
        cls._alert_service = None
        cls._watchlist_service = None


# FastAPI dependency functions
def get_auth_service() -> IAuthService:
    """FastAPI dependency for auth service."""
    return ServiceFactory.get_auth_service()


def get_market_data_service() -> IMarketDataService:
    """FastAPI dependency for market data service."""
    return ServiceFactory.get_market_data_service()


def get_portfolio_service() -> IPortfolioService:
    """FastAPI dependency for portfolio service."""
    return ServiceFactory.get_portfolio_service()


def get_alert_service() -> IAlertService:
    """FastAPI dependency for alert service."""
    return ServiceFactory.get_alert_service()


def get_watchlist_service() -> IWatchlistService:
    """FastAPI dependency for watchlist service."""
    return ServiceFactory.get_watchlist_service()

