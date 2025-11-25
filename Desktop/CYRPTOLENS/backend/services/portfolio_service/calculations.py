"""
Portfolio calculation functions.
Calculates value, distribution, profit/loss, risk, volatility.
"""
from typing import List, Dict, Tuple
from decimal import Decimal
from shared.models import Portfolio, MarketCache
from sqlalchemy.orm import Session


class PortfolioCalculations:
    """Service for portfolio calculations."""
    
    @staticmethod
    def calculate_item_value(
        amount: Decimal, current_price: Decimal
    ) -> Decimal:
        """Calculate total value of a portfolio item."""
        return amount * current_price
    
    @staticmethod
    def calculate_profit_loss(
        amount: Decimal, buy_price: Decimal, current_price: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate profit/loss and percentage.
        Returns: (profit_loss, profit_loss_percent)
        """
        total_cost = amount * buy_price
        total_value = amount * current_price
        profit_loss = total_value - total_cost
        profit_loss_percent = (
            (profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)
        )
        return profit_loss, profit_loss_percent
    
    @staticmethod
    def calculate_total_portfolio_value(
        items: List[Portfolio], current_prices: Dict[str, Decimal]
    ) -> Decimal:
        """Calculate total portfolio value."""
        total = Decimal(0)
        for item in items:
            price = current_prices.get(item.coin_symbol.upper(), Decimal(0))
            total += item.amount * price
        return total
    
    @staticmethod
    def calculate_total_profit_loss(
        items: List[Portfolio], current_prices: Dict[str, Decimal]
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate total profit/loss and percentage.
        Returns: (total_profit_loss, total_profit_loss_percent)
        """
        total_cost = Decimal(0)
        total_value = Decimal(0)
        
        for item in items:
            price = current_prices.get(item.coin_symbol.upper(), Decimal(0))
            total_cost += item.amount * item.buy_price
            total_value += item.amount * price
        
        total_profit_loss = total_value - total_cost
        total_profit_loss_percent = (
            (total_profit_loss / total_cost * 100) if total_cost > 0 else Decimal(0)
        )
        
        return total_profit_loss, total_profit_loss_percent
    
    @staticmethod
    def calculate_distribution(
        items: List[Portfolio],
        current_prices: Dict[str, Decimal],
        total_value: Decimal
    ) -> List[Dict]:
        """
        Calculate portfolio distribution.
        Returns list of distribution items with percentages.
        """
        if total_value == 0:
            return []
        
        distribution = []
        for item in items:
            price = current_prices.get(item.coin_symbol.upper(), Decimal(0))
            value = item.amount * price
            percentage = (value / total_value * 100) if total_value > 0 else Decimal(0)
            
            profit_loss, profit_loss_percent = PortfolioCalculations.calculate_profit_loss(
                item.amount, item.buy_price, price
            )
            
            distribution.append({
                "coin_symbol": item.coin_symbol.upper(),
                "amount": item.amount,
                "value": value,
                "percentage": percentage,
                "profit_loss": profit_loss,
                "profit_loss_percent": profit_loss_percent,
            })
        
        return distribution
    
    @staticmethod
    def calculate_risk_score(
        items: List[Portfolio], current_prices: Dict[str, Decimal]
    ) -> Decimal:
        """
        Calculate portfolio risk score (0-100).
        Higher score = higher risk.
        Based on concentration and volatility.
        """
        if not items:
            return Decimal(0)
        
        # Get distribution
        total_value = PortfolioCalculations.calculate_total_portfolio_value(
            items, current_prices
        )
        distribution = PortfolioCalculations.calculate_distribution(
            items, current_prices, total_value
        )
        
        # Calculate concentration risk (Herfindahl index)
        concentration = sum([d["percentage"] ** 2 for d in distribution]) / 10000
        
        # Risk score: 0-100 based on concentration
        # Higher concentration = higher risk
        risk_score = min(Decimal(100), concentration * 100)
        
        return risk_score
    
    @staticmethod
    def calculate_volatility_score(
        items: List[Portfolio], current_prices: Dict[str, Decimal]
    ) -> Decimal:
        """
        Calculate portfolio volatility score (0-100).
        Based on price changes (simplified - would use historical data in production).
        """
        if not items:
            return Decimal(0)
        
        # Simplified volatility calculation
        # In production, would use historical price data
        total_volatility = Decimal(0)
        count = 0
        
        for item in items:
            price = current_prices.get(item.coin_symbol.upper(), Decimal(0))
            if price > 0 and item.buy_price > 0:
                # Calculate price change percentage
                price_change = abs((price - item.buy_price) / item.buy_price * 100)
                total_volatility += price_change
                count += 1
        
        if count == 0:
            return Decimal(0)
        
        avg_volatility = total_volatility / count
        # Normalize to 0-100 scale
        volatility_score = min(Decimal(100), avg_volatility)
        
        return volatility_score
    
    @staticmethod
    def get_current_prices(
        db: Session, coin_symbols: List[str]
    ) -> Dict[str, Decimal]:
        """Get current prices for multiple coins from market_cache."""
        from sqlalchemy import select
        from shared.models import MarketCache
        
        prices = {}
        for symbol in coin_symbols:
            stmt = select(MarketCache).where(
                MarketCache.symbol == symbol.upper()
            )
            result = db.execute(stmt)
            market_data = result.scalar_one_or_none()
            if market_data:
                prices[symbol.upper()] = market_data.price
            else:
                prices[symbol.upper()] = Decimal(0)
        
        return prices

