"""
Main business logic service for Portfolio Service.
Orchestrates database operations and calculations.
Following CryptoLens Data Architecture Specification.
Portfolio valuation uses CoinGecko prices as canonical source.
"""
# Standard library imports
import random
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

# Third-party imports
from sqlalchemy.orm import Session

# Local application imports
from shared.analytics.portfolio import (
    PortfolioHolding,
    calculate_allocation,
    calculate_diversification_score,
    calculate_pnl,
    calculate_portfolio_risk_score,
    calculate_portfolio_value,
    calculate_portfolio_volatility,
)
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.repositories.crypto_data_repository import CryptoDataRepository
from .database_service import PortfolioDatabaseService
from .calculations import PortfolioCalculations
from .advanced_analytics import AdvancedAnalyticsService
from .tax_service import TaxService
from .rebalancing_service import RebalancingService
from .historical_service import HistoricalService
from .dca_service import DCAService
from .export_service import ExportService
from .models import (
    PortfolioResponse,
    PortfolioItemResponse,
    PortfolioDistributionItem,
    PortfolioAddResponse,
    PortfolioEditResponse,
    PortfolioRemoveResponse,
)


class PortfolioService:
    """Main service for portfolio operations."""
    
    def __init__(self):
        # Initialize repository for CoinGecko prices (following architecture spec)
        market_provider = CoinGeckoMarketDataProvider()
        ohlc_provider = BinanceOhlcDataProvider()
        self.repository = CryptoDataRepository(market_provider, ohlc_provider)
        
        self.db_service = PortfolioDatabaseService()
        self.calculations = PortfolioCalculations()
        self.advanced_analytics = AdvancedAnalyticsService()
        self.tax_service = TaxService()
        self.rebalancing_service = RebalancingService()
        self.historical_service = HistoricalService()
        self.dca_service = DCAService()
        self.export_service = ExportService()
        
        # Add coin-specific methods
        from .coin_methods import add_coin_methods_to_service
        add_coin_methods_to_service(self)
    
    async def get_portfolio(
        self, db: Session, user_id: UUID
    ) -> PortfolioResponse:
        """Get complete portfolio with calculations."""
        # Get portfolio items
        items = self.db_service.get_user_portfolio(db, user_id)
        
        if not items:
            return PortfolioResponse(
                total_value=Decimal(0),
                total_profit_loss=Decimal(0),
                total_profit_loss_percent=Decimal(0),
                items=[],
                distribution=[],
                updated_at=datetime.utcnow()
            )
        
        # Get current prices for all coins from CoinGecko (following architecture spec)
        coin_symbols = [item.coin_symbol.upper() for item in items]
        price_data_map = await self.repository.get_portfolio_data(coin_symbols)
        
        # Convert PriceData to Decimal prices dict
        current_prices = {
            symbol: price_data.price 
            for symbol, price_data in price_data_map.items()
        }
        
        # Fill missing prices with 0
        for symbol in coin_symbols:
            if symbol not in current_prices:
                current_prices[symbol] = Decimal(0)
        
        # Convert to PortfolioHolding format for analytics engine
        holdings = [
            PortfolioHolding(
                symbol=item.coin_symbol.upper(),
                amount=item.amount,
                buy_price=item.buy_price,
                current_price=current_prices.get(item.coin_symbol.upper(), Decimal(0))
            )
            for item in items
        ]
        
        # Calculate portfolio metrics using analytics engine (following specification)
        total_value = calculate_portfolio_value(holdings)
        
        # Calculate PNL
        pnl_data = calculate_pnl(holdings)
        total_profit_loss = sum([data["pnl"] for data in pnl_data.values()])
        total_cost = sum([h.amount * (h.buy_price or Decimal(0)) for h in holdings])
        total_profit_loss_percent = (
            (total_profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)
        )
        
        # Build item responses
        item_responses = []
        for item in items:
            current_price = current_prices.get(
                item.coin_symbol.upper(), Decimal(0)
            )
            total_item_value = self.calculations.calculate_item_value(
                item.amount, current_price
            )
            profit_loss, profit_loss_percent = (
                self.calculations.calculate_profit_loss(
                    item.amount, item.buy_price, current_price
                )
            )
            
            item_responses.append(
                PortfolioItemResponse(
                    id=item.id,
                    coin_symbol=item.coin_symbol,
                    amount=item.amount,
                    buy_price=item.buy_price,
                    current_price=current_price,
                    total_value=total_item_value,
                    profit_loss=profit_loss,
                    profit_loss_percent=profit_loss_percent,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )
        
        # Calculate allocation using analytics engine
        allocation = calculate_allocation(holdings)
        
        # Build distribution from allocation
        distribution_data = []
        for item in items:
            symbol = item.coin_symbol.upper()
            weight = allocation.get(symbol, Decimal(0))
            value = item.amount * current_prices.get(symbol, Decimal(0))
            pnl_info = pnl_data.get(symbol, {"pnl": Decimal(0), "pnlPercent": Decimal(0)})
            
            distribution_data.append({
                "coin_symbol": symbol,
                "amount": item.amount,
                "value": value,
                "percentage": weight * Decimal(100),  # Convert to percentage
                "profit_loss": pnl_info["pnl"],
                "profit_loss_percent": pnl_info["pnlPercent"],
            })
        
        distribution = [
            PortfolioDistributionItem(**d) for d in distribution_data
        ]
        
        # Calculate risk and volatility scores using analytics engine
        risk_score = calculate_portfolio_risk_score(holdings)
        volatility_score = calculate_portfolio_volatility(holdings)
        
        return PortfolioResponse(
            total_value=total_value,
            total_profit_loss=total_profit_loss,
            total_profit_loss_percent=total_profit_loss_percent,
            items=item_responses,
            distribution=distribution,
            risk_score=risk_score,
            volatility_score=volatility_score,
            updated_at=datetime.utcnow()
        )
    
    async def add_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        amount: Decimal,
        buy_price: Decimal
    ) -> PortfolioAddResponse:
        """Add a new portfolio item."""
        item = self.db_service.add_portfolio_item(
            db, user_id, coin_symbol, amount, buy_price
        )
        
        # Get current price from CoinGecko (following architecture spec)
        price_data_map = await self.repository.get_portfolio_data([coin_symbol.upper()])
        price_data = price_data_map.get(coin_symbol.upper())
        current_price = price_data.price if price_data else buy_price
        
        # Calculate values
        total_value = self.calculations.calculate_item_value(
            item.amount, current_price
        )
        profit_loss, profit_loss_percent = (
            self.calculations.calculate_profit_loss(
                item.amount, item.buy_price, current_price
            )
        )
        
        item_response = PortfolioItemResponse(
            id=item.id,
            coin_symbol=item.coin_symbol,
            amount=item.amount,
            buy_price=item.buy_price,
            current_price=current_price,
            total_value=total_value,
            profit_loss=profit_loss,
            profit_loss_percent=profit_loss_percent,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        
        return PortfolioAddResponse(
            success=True,
            message="Portfolio item added successfully",
            item=item_response
        )
    
    async def edit_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        item_id: UUID,
        amount: Decimal = None,
        buy_price: Decimal = None
    ) -> PortfolioEditResponse:
        """Edit a portfolio item."""
        item = self.db_service.update_portfolio_item(
            db, user_id, item_id, amount, buy_price
        )
        
        if not item:
            return PortfolioEditResponse(
                success=False,
                message="Portfolio item not found",
                item=None
            )
        
        # Get current price from CoinGecko (following architecture spec)
        price_data_map = await self.repository.get_portfolio_data([item.coin_symbol.upper()])
        price_data = price_data_map.get(item.coin_symbol.upper())
        current_price = price_data.price if price_data else item.buy_price
        
        # Calculate values
        total_value = self.calculations.calculate_item_value(
            item.amount, current_price
        )
        profit_loss, profit_loss_percent = (
            self.calculations.calculate_profit_loss(
                item.amount, item.buy_price, current_price
            )
        )
        
        item_response = PortfolioItemResponse(
            id=item.id,
            coin_symbol=item.coin_symbol,
            amount=item.amount,
            buy_price=item.buy_price,
            current_price=current_price,
            total_value=total_value,
            profit_loss=profit_loss,
            profit_loss_percent=profit_loss_percent,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        
        return PortfolioEditResponse(
            success=True,
            message="Portfolio item updated successfully",
            item=item_response
        )
    
    def remove_portfolio_item(
        self, db: Session, user_id: UUID, item_id: UUID
    ) -> PortfolioRemoveResponse:
        """Remove a portfolio item."""
        success = self.db_service.delete_portfolio_item(db, user_id, item_id)
        
        if success:
            return PortfolioRemoveResponse(
                success=True,
                message="Portfolio item removed successfully"
            )
        else:
            return PortfolioRemoveResponse(
                success=False,
                message="Portfolio item not found"
            )
    
    async def get_portfolio_performance(
        self, db: Session, user_id: UUID, timeframe: str = "1D"
    ) -> dict:
        """Get portfolio performance data for different timeframes."""
        try:
            # Get current portfolio value
            portfolio = await self.get_portfolio(db, user_id)
            current_value = float(portfolio.total_value)
            
            # Generate performance data based on current value
            # In production, this would fetch historical data from database
            performance_data = {}
            
            # Generate data for all timeframes
            timeframes = {
                "1D": 24,  # 24 hours
                "7D": 7,   # 7 days
                "30D": 30, # 30 days
                "1Y": 12   # 12 months
            }
            
            import random
            for tf, count in timeframes.items():
                values = []
                base_value = current_value
                
                for i in range(count):
                    # Simulate value changes
                    # Earlier values have more variation
                    variation_factor = (count - i) / count
                    variation = random.uniform(-0.05, 0.05) * variation_factor
                    value = base_value * (1 + variation)
                    values.append(round(value, 2))
                
                performance_data[tf] = values
            
            return performance_data
        except Exception as e:
            import logging
            logging.error(f"Error fetching performance data: {e}")
            return {}
    
    async def get_transaction_history(
        self, db: Session, user_id: UUID, limit: int = 50
    ) -> List[dict]:
        """Get transaction history for user's portfolio."""
        try:
            # Get portfolio items
            items = self.db_service.get_user_portfolio(db, user_id)
            
            transactions = []
            for item in items:
                # Create a buy transaction for each portfolio item
                # In production, this would come from a transactions table
                transactions.append({
                    "symbol": item.coin_symbol.upper(),
                    "type": "buy",
                    "quantity": float(item.amount),
                    "price": float(item.buy_price),
                    "amount": float(item.amount * item.buy_price),
                    "date": item.created_at.isoformat() if item.created_at else datetime.utcnow().isoformat()
                })
            
            # Sort by date (newest first)
            transactions.sort(key=lambda x: x["date"], reverse=True)
            
            # Limit results
            return transactions[:limit]
        except Exception as e:
            import logging
            logging.error(f"Error fetching transaction history: {e}")
            return []
    
    # ============================================================
    # PREMIUM FEATURES METHODS (from premium_methods.py)
    # ============================================================
    
    async def get_wallets(self, db: Session, user_id: UUID):
        """Get all wallets for a user."""
        wallets = self.db_service.get_user_wallets(db, user_id)
        return [
            {
                'id': str(w.id),
                'user_id': str(w.user_id),
                'name': w.name,
                'description': w.description,
                'color': w.color,
                'is_default': w.is_default,
                'created_at': w.created_at.isoformat(),
                'updated_at': w.updated_at.isoformat()
            }
            for w in wallets
        ]
    
    async def create_wallet(
        self,
        db: Session,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_default: bool = False
    ):
        """Create a new wallet."""
        wallet = self.db_service.create_wallet(
            db, user_id, name, description, color, is_default
        )
        return {
            'id': str(wallet.id),
            'user_id': str(wallet.user_id),
            'name': wallet.name,
            'description': wallet.description,
            'color': wallet.color,
            'is_default': wallet.is_default,
            'created_at': wallet.created_at.isoformat(),
            'updated_at': wallet.updated_at.isoformat()
        }
    
    async def get_sharpe_ratio(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        timeframe: str = '30D'
    ):
        """Calculate Sharpe Ratio."""
        snapshots = self.db_service.get_snapshots(db, user_id, wallet_id)
        if len(snapshots) < 2:
            return {
                'sharpe_ratio': Decimal('0'),
                'portfolio_return': Decimal('0'),
                'risk_free_rate': self.advanced_analytics.RISK_FREE_RATE,
                'portfolio_volatility': Decimal('0'),
                'timeframe': timeframe
            }
        
        returns = self.historical_service.calculate_portfolio_returns(snapshots)
        sharpe, portfolio_return, risk_free, volatility = self.advanced_analytics.calculate_sharpe_ratio(returns)
        
        return {
            'sharpe_ratio': sharpe,
            'portfolio_return': portfolio_return,
            'risk_free_rate': risk_free,
            'portfolio_volatility': volatility,
            'timeframe': timeframe
        }
    
    async def get_alpha_beta(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        benchmark: str = 'BTC',
        timeframe: str = '30D'
    ):
        """Calculate Alpha and Beta."""
        snapshots = self.db_service.get_snapshots(db, user_id, wallet_id)
        portfolio_returns = self.historical_service.calculate_portfolio_returns(snapshots)
        benchmark_returns = portfolio_returns  # Placeholder - fetch from market data in production
        
        alpha, beta = self.advanced_analytics.calculate_alpha_beta(
            portfolio_returns, benchmark_returns
        )
        
        return {
            'alpha': alpha,
            'beta': beta,
            'benchmark': benchmark,
            'timeframe': timeframe
        }
    
    async def get_realized_unrealized(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None
    ):
        """Get realized and unrealized gains/losses."""
        transactions = self.db_service.get_user_transactions(db, user_id, wallet_id)
        items = self.db_service.get_user_portfolio(db, user_id)
        
        tx_dicts = [
            {
                'transaction_type': tx.transaction_type,
                'coin_symbol': tx.coin_symbol,
                'amount': tx.amount,
                'price': tx.price,
                'profit_loss': Decimal('0')
            }
            for tx in transactions
        ]
        
        coin_symbols = [item.coin_symbol.upper() for item in items]
        price_data_map = await self.repository.get_portfolio_data(coin_symbols)
        current_prices = {
            symbol: price_data.price
            for symbol, price_data in price_data_map.items()
        }
        
        holdings_dicts = [
            {
                'coin_symbol': item.coin_symbol,
                'amount': item.amount,
                'buy_price': item.buy_price
            }
            for item in items
        ]
        
        result = self.tax_service.calculate_realized_unrealized(
            tx_dicts, holdings_dicts, current_prices
        )
        return result
    
    async def get_rebalancing_suggestions(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None
    ):
        """Get rebalancing suggestions."""
        portfolio = await self.get_portfolio(db, user_id)
        targets = self.db_service.get_rebalancing_targets(db, user_id, wallet_id)
        target_allocations = {t.coin_symbol: t.target_percentage for t in targets}
        
        if not target_allocations:
            return {
                'suggestions': [],
                'total_deviation': Decimal('0'),
                'needs_rebalancing': False
            }
        
        holdings = [
            PortfolioHolding(
                symbol=item.coin_symbol.upper(),
                amount=item.amount,
                buy_price=item.buy_price,
                current_price=Decimal(str(item.current_price))
            )
            for item in portfolio.items
        ]
        
        tolerance = targets[0].tolerance if targets else Decimal('5.0')
        suggestions = self.rebalancing_service.calculate_rebalancing_suggestions(
            holdings, portfolio.total_value, target_allocations, tolerance
        )
        
        current_allocation = self.rebalancing_service.calculate_current_allocation(
            holdings, portfolio.total_value
        )
        total_deviation = self.rebalancing_service.calculate_total_deviation(
            current_allocation, target_allocations
        )
        needs_rebalancing = self.rebalancing_service.needs_rebalancing(
            current_allocation, target_allocations, tolerance
        )
        
        return {
            'suggestions': suggestions,
            'total_deviation': total_deviation,
            'needs_rebalancing': needs_rebalancing
        }
    
    async def export_portfolio(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        format: str = 'pdf',
        period: str = 'ALL'
    ):
        """Export portfolio data."""
        portfolio = await self.get_portfolio(db, user_id)
        
        # Get transactions if available
        transactions = self.db_service.get_user_transactions(db, user_id, wallet_id, limit=1000)
        
        portfolio_data = {
            'total_value': portfolio.total_value,
            'total_cost': sum([item.amount * item.buy_price for item in portfolio.items]),
            'total_profit_loss': portfolio.total_profit_loss,
            'total_profit_loss_percent': portfolio.total_profit_loss_percent,
            'items': [
                {
                    'coin_symbol': item.coin_symbol,
                    'amount': float(item.amount),
                    'buy_price': float(item.buy_price),
                    'current_price': float(item.current_price),
                    'total_value': float(item.total_value),
                    'profit_loss': float(item.profit_loss),
                    'profit_loss_percent': float(item.profit_loss_percent)
                }
                for item in portfolio.items
            ],
            'transactions': [
                {
                    'transaction_date': tx.transaction_date.isoformat(),
                    'transaction_type': tx.transaction_type,
                    'coin_symbol': tx.coin_symbol,
                    'amount': float(tx.amount),
                    'price': float(tx.price),
                    'fee': float(tx.fee),
                    'total_cost': float(tx.total_cost),
                }
                for tx in transactions
            ]
        }
        
        if format == 'pdf':
            return self.export_service.generate_pdf_report(portfolio_data, period)
        elif format == 'csv':
            return self.export_service.generate_csv_export(portfolio_data, 'full')
        elif format == 'excel':
            return self.export_service.generate_excel_export(portfolio_data)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # ============================================================
    # PREMIUM FEATURES: WALLET METHODS
    # ============================================================
    
    async def get_wallets(self, db: Session, user_id: UUID):
        """Get all wallets for a user."""
        wallets = self.db_service.get_user_wallets(db, user_id)
        return [
            {
                'id': str(w.id),
                'user_id': str(w.user_id),
                'name': w.name,
                'description': w.description,
                'color': w.color,
                'is_default': w.is_default,
                'created_at': w.created_at.isoformat(),
                'updated_at': w.updated_at.isoformat()
            }
            for w in wallets
        ]
    
    async def create_wallet(
        self,
        db: Session,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_default: bool = False
    ):
        """Create a new wallet."""
        wallet = self.db_service.create_wallet(
            db, user_id, name, description, color, is_default
        )
        return {
            'id': str(wallet.id),
            'user_id': str(wallet.user_id),
            'name': wallet.name,
            'description': wallet.description,
            'color': wallet.color,
            'is_default': wallet.is_default,
            'created_at': wallet.created_at.isoformat(),
            'updated_at': wallet.updated_at.isoformat()
        }

