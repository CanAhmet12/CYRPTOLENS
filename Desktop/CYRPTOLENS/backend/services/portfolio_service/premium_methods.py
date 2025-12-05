"""
Premium Portfolio Methods
Additional methods for premium features that extend PortfolioService.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
from sqlalchemy.orm import Session
from shared.analytics.portfolio import PortfolioHolding


# This will be mixed into PortfolioService
# Methods are defined here but will be added directly to PortfolioService class
    """Premium methods mixin for PortfolioService."""
    
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
        
        # Get benchmark returns (simplified - in production, fetch from market data)
        benchmark_returns = portfolio_returns  # Placeholder
        
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
        
        portfolio_data = {
            'total_value': portfolio.total_value,
            'total_cost': sum([item.amount * item.buy_price for item in portfolio.items]),
            'total_profit_loss': portfolio.total_profit_loss,
            'total_profit_loss_percent': portfolio.total_profit_loss_percent,
            'items': [
                {
                    'coin_symbol': item.coin_symbol,
                    'amount': item.amount,
                    'buy_price': item.buy_price,
                    'current_price': item.current_price,
                    'total_value': item.total_value,
                    'profit_loss': item.profit_loss,
                    'profit_loss_percent': item.profit_loss_percent
                }
                for item in portfolio.items
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

