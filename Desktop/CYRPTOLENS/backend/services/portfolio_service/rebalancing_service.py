"""
Rebalancing Service for Portfolio.
Handles target allocation, rebalancing suggestions, deviation alerts.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from uuid import UUID
from shared.analytics.portfolio import PortfolioHolding


class RebalancingService:
    """Service for portfolio rebalancing calculations."""
    
    def calculate_current_allocation(
        self,
        holdings: List[PortfolioHolding],
        total_value: Decimal
    ) -> Dict[str, Decimal]:
        """
        Calculate current allocation percentages.
        
        Args:
            holdings: List of portfolio holdings
            total_value: Total portfolio value
        
        Returns:
            Dict mapping coin_symbol to percentage
        """
        allocation = {}
        
        if total_value == 0:
            return allocation
        
        for holding in holdings:
            coin_value = holding.amount * holding.current_price
            percentage = (coin_value / total_value * Decimal('100')) if total_value > 0 else Decimal('0')
            allocation[holding.symbol] = percentage
        
        return allocation
    
    def calculate_rebalancing_suggestions(
        self,
        holdings: List[PortfolioHolding],
        total_value: Decimal,
        target_allocations: Dict[str, Decimal],
        tolerance: Decimal = Decimal('5.0')
    ) -> List[Dict[str, any]]:
        """
        Calculate rebalancing suggestions.
        
        Args:
            holdings: List of portfolio holdings
            total_value: Total portfolio value
            target_allocations: Dict mapping coin_symbol to target percentage
            tolerance: Deviation tolerance in percentage
        
        Returns:
            List of suggestion dicts
        """
        suggestions = []
        current_allocation = self.calculate_current_allocation(holdings, total_value)
        
        # Check all target allocations
        for coin_symbol, target_percent in target_allocations.items():
            current_percent = current_allocation.get(coin_symbol, Decimal('0'))
            deviation = abs(current_percent - target_percent)
            
            if deviation > tolerance:
                # Calculate suggested action
                if current_percent < target_percent:
                    # Need to buy more
                    target_value = total_value * target_percent / Decimal('100')
                    current_value = total_value * current_percent / Decimal('100')
                    suggested_value = target_value - current_value
                    
                    # Find holding to get current price
                    holding = next((h for h in holdings if h.symbol == coin_symbol), None)
                    if holding and holding.current_price > 0:
                        suggested_amount = suggested_value / holding.current_price
                        suggestions.append({
                            'coin_symbol': coin_symbol,
                            'current_percentage': current_percent,
                            'target_percentage': target_percent,
                            'deviation': deviation,
                            'suggested_action': 'buy',
                            'suggested_amount': suggested_amount,
                            'suggested_value': suggested_value
                        })
                else:
                    # Need to sell some
                    target_value = total_value * target_percent / Decimal('100')
                    current_value = total_value * current_percent / Decimal('100')
                    suggested_value = current_value - target_value
                    
                    # Find holding to get current price
                    holding = next((h for h in holdings if h.symbol == coin_symbol), None)
                    if holding and holding.current_price > 0:
                        suggested_amount = suggested_value / holding.current_price
                        suggestions.append({
                            'coin_symbol': coin_symbol,
                            'current_percentage': current_percent,
                            'target_percentage': target_percent,
                            'deviation': deviation,
                            'suggested_action': 'sell',
                            'suggested_amount': suggested_amount,
                            'suggested_value': suggested_value
                        })
        
        # Check for coins in portfolio but not in targets (suggest to sell)
        for holding in holdings:
            if holding.symbol not in target_allocations:
                current_percent = current_allocation.get(holding.symbol, Decimal('0'))
                if current_percent > tolerance:
                    current_value = total_value * current_percent / Decimal('100')
                    suggestions.append({
                        'coin_symbol': holding.symbol,
                        'current_percentage': current_percent,
                        'target_percentage': Decimal('0'),
                        'deviation': current_percent,
                        'suggested_action': 'sell',
                        'suggested_amount': holding.amount,
                        'suggested_value': current_value
                    })
        
        # Sort by deviation (descending)
        suggestions.sort(key=lambda x: x['deviation'], reverse=True)
        
        return suggestions
    
    def calculate_total_deviation(
        self,
        current_allocation: Dict[str, Decimal],
        target_allocations: Dict[str, Decimal]
    ) -> Decimal:
        """
        Calculate total deviation from target allocation.
        
        Args:
            current_allocation: Current allocation percentages
            target_allocations: Target allocation percentages
        
        Returns:
            Total deviation percentage
        """
        total_deviation = Decimal('0')
        
        # Check all target allocations
        for coin_symbol, target_percent in target_allocations.items():
            current_percent = current_allocation.get(coin_symbol, Decimal('0'))
            deviation = abs(current_percent - target_percent)
            total_deviation += deviation
        
        # Check for coins in current but not in targets
        for coin_symbol, current_percent in current_allocation.items():
            if coin_symbol not in target_allocations:
                total_deviation += current_percent
        
        return total_deviation
    
    def needs_rebalancing(
        self,
        current_allocation: Dict[str, Decimal],
        target_allocations: Dict[str, Decimal],
        tolerance: Decimal = Decimal('5.0')
    ) -> bool:
        """
        Check if portfolio needs rebalancing.
        
        Args:
            current_allocation: Current allocation percentages
            target_allocations: Target allocation percentages
            tolerance: Deviation tolerance in percentage
        
        Returns:
            True if rebalancing is needed
        """
        for coin_symbol, target_percent in target_allocations.items():
            current_percent = current_allocation.get(coin_symbol, Decimal('0'))
            deviation = abs(current_percent - target_percent)
            if deviation > tolerance:
                return True
        
        # Check for coins in current but not in targets
        for coin_symbol, current_percent in current_allocation.items():
            if coin_symbol not in target_allocations and current_percent > tolerance:
                return True
        
        return False

