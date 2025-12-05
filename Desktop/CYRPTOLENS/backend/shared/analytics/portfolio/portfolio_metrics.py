"""
Portfolio Metrics
Following Indicator & Analytics Engine Specification exactly.

Metrics:
1. Total Portfolio Value: sum(value_i) where value_i = amount_i * currentPrice_i
2. PNL per asset: pnl_i = (currentPrice_i - buyPrice_i) * amount_i
3. Allocation: weight_i = value_i / totalPortfolioValue
4. Diversification Score: 1 - HHI where HHI = sum(weight_i^2)
5. Portfolio Volatility: Weighted average of asset volatility
6. Portfolio Risk Score: Combination of concentration risk and volatility
"""
from typing import List, Dict, Optional
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class PortfolioHolding:
    """Portfolio holding data."""
    symbol: str
    amount: Decimal
    buy_price: Optional[Decimal] = None
    current_price: Decimal = Decimal(0)
    volatility: Optional[Decimal] = None  # Optional per-coin volatility


def calculate_portfolio_value(holdings: List[PortfolioHolding]) -> Decimal:
    """
    Calculate total portfolio value.
    
    Formula: sum(amount_i * currentPrice_i)
    """
    total = Decimal(0)
    for holding in holdings:
        if holding.current_price > 0:
            total += holding.amount * holding.current_price
    return total


def calculate_pnl(holdings: List[PortfolioHolding]) -> Dict[str, Dict[str, Decimal]]:
    """
    Calculate profit/loss per asset.
    
    Returns:
        Dictionary mapping symbol to:
        - pnl: Absolute PNL
        - pnlPercent: Percentage PNL
    """
    pnl_data = {}
    
    for holding in holdings:
        if holding.buy_price is None or holding.buy_price == 0:
            pnl_data[holding.symbol] = {
                "pnl": Decimal(0),
                "pnlPercent": Decimal(0)
            }
            continue
        
        if holding.current_price == 0:
            pnl_data[holding.symbol] = {
                "pnl": Decimal(0),
                "pnlPercent": Decimal(0)
            }
            continue
        
        # Calculate PNL
        pnl = (holding.current_price - holding.buy_price) * holding.amount
        pnl_percent = ((holding.current_price - holding.buy_price) / holding.buy_price) * Decimal(100)
        
        pnl_data[holding.symbol] = {
            "pnl": pnl,
            "pnlPercent": pnl_percent
        }
    
    return pnl_data


def calculate_allocation(holdings: List[PortfolioHolding]) -> Dict[str, Decimal]:
    """
    Calculate allocation (weight) per asset.
    
    Formula: weight_i = value_i / totalPortfolioValue
    """
    total_value = calculate_portfolio_value(holdings)
    
    if total_value == 0:
        return {holding.symbol: Decimal(0) for holding in holdings}
    
    allocation = {}
    for holding in holdings:
        if holding.current_price > 0:
            value = holding.amount * holding.current_price
            weight = value / total_value
            allocation[holding.symbol] = weight
        else:
            allocation[holding.symbol] = Decimal(0)
    
    return allocation


def calculate_diversification_score(holdings: List[PortfolioHolding]) -> Decimal:
    """
    Calculate diversification score using Herfindahl-Hirschman Index (HHI).
    
    Formula:
    - HHI = sum(weight_i^2)
    - DiversificationScore = 1 - HHI
    - Map to 0-100 if needed
    
    Returns:
        Diversification score (0-100)
    """
    if not holdings:
        return Decimal(0)
    
    allocation = calculate_allocation(holdings)
    
    # Calculate HHI
    hhi = sum([weight ** 2 for weight in allocation.values()])
    
    # Diversification score (0-1)
    diversification = Decimal(1) - hhi
    
    # Map to 0-100
    return diversification * Decimal(100)


def calculate_portfolio_volatility(
    holdings: List[PortfolioHolding]
) -> Decimal:
    """
    Calculate portfolio volatility.
    
    Option A: Weighted average of asset volatility (if we have per-coin sigma).
    Option B: Simple proxy based on concentration and volatility of top holdings.
    
    Returns:
        Portfolio volatility score (0-100)
    """
    if not holdings:
        return Decimal(0)
    
    allocation = calculate_allocation(holdings)
    
    # Option A: Weighted average if volatility data available
    volatilities_available = any(h.volatility is not None for h in holdings)
    
    if volatilities_available:
        weighted_vol = Decimal(0)
        for holding in holdings:
            if holding.volatility is not None:
                weight = allocation.get(holding.symbol, Decimal(0))
                weighted_vol += weight * holding.volatility
        
        # Normalize to 0-100
        return min(weighted_vol * Decimal(100), Decimal(100))
    
    # Option B: Simple proxy based on concentration
    # Higher concentration + higher volatility assets → higher risk
    diversification = calculate_diversification_score(holdings)
    concentration_risk = Decimal(100) - diversification
    
    # Assume average volatility of 0.03 (3%) for crypto
    base_volatility = Decimal("0.03")
    
    # Adjust based on concentration
    portfolio_volatility = base_volatility * (Decimal(1) + concentration_risk / Decimal(100))
    
    # Normalize to 0-100
    return min(portfolio_volatility * Decimal(100), Decimal(100))


def calculate_portfolio_risk_score(holdings: List[PortfolioHolding]) -> Decimal:
    """
    Calculate portfolio risk score.
    
    Combination of:
    - Concentration risk (HHI)
    - Average volatility of top holdings
    
    Returns:
        Risk score (0-100)
    """
    if not holdings:
        return Decimal(0)
    
    # Get concentration risk (inverse of diversification)
    diversification = calculate_diversification_score(holdings)
    concentration_risk = Decimal(100) - diversification
    
    # Get portfolio volatility
    portfolio_vol = calculate_portfolio_volatility(holdings)
    
    # Combine: 50% concentration risk, 50% volatility
    risk_score = (concentration_risk * Decimal("0.5")) + (portfolio_vol * Decimal("0.5"))
    
    # Clamp to 0-100
    return max(Decimal(0), min(risk_score, Decimal(100)))

