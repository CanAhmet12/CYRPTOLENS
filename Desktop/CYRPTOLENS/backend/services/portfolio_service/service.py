"""
Main business logic service for Portfolio Service.
Orchestrates database operations and calculations.
Following CryptoLens Data Architecture Specification.
Portfolio valuation uses CoinGecko prices as canonical source.
"""
from typing import List, Dict
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
import random
from shared.data_providers.coingecko_provider import CoinGeckoMarketDataProvider
from shared.data_providers.binance_provider import BinanceOhlcDataProvider
from shared.repositories.crypto_data_repository import CryptoDataRepository
from shared.analytics.portfolio import (
    PortfolioHolding,
    calculate_portfolio_value,
    calculate_pnl,
    calculate_allocation,
    calculate_diversification_score,
    calculate_portfolio_volatility,
    calculate_portfolio_risk_score,
)
from .database_service import PortfolioDatabaseService
from .calculations import PortfolioCalculations
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

