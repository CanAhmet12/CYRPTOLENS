"""
Unit tests for Portfolio Metrics.
Following Indicator & Analytics Engine Specification exactly.
"""
import unittest
from decimal import Decimal
from ..portfolio.portfolio_metrics import (
    PortfolioHolding,
    calculate_portfolio_value,
    calculate_pnl,
    calculate_allocation,
    calculate_diversification_score,
    calculate_portfolio_risk_score,
)


class TestPortfolioMetrics(unittest.TestCase):
    """Test Portfolio Metrics calculations."""
    
    def test_portfolio_value(self):
        """Test portfolio value calculation."""
        holdings = [
            PortfolioHolding(
                symbol="BTC",
                amount=Decimal("0.5"),
                current_price=Decimal("50000")
            ),
            PortfolioHolding(
                symbol="ETH",
                amount=Decimal("2"),
                current_price=Decimal("3000")
            ),
        ]
        
        total = calculate_portfolio_value(holdings)
        expected = Decimal("0.5") * Decimal("50000") + Decimal("2") * Decimal("3000")
        self.assertEqual(total, expected)
    
    def test_allocation(self):
        """Test allocation calculation."""
        holdings = [
            PortfolioHolding(
                symbol="BTC",
                amount=Decimal("0.5"),
                current_price=Decimal("50000")
            ),
            PortfolioHolding(
                symbol="ETH",
                amount=Decimal("2"),
                current_price=Decimal("3000")
            ),
        ]
        
        allocation = calculate_allocation(holdings)
        total_value = calculate_portfolio_value(holdings)
        
        # Weights should sum to 1
        total_weight = sum(allocation.values())
        self.assertAlmostEqual(float(total_weight), 1.0, places=2)
    
    def test_diversification_hhi(self):
        """Test diversification score using HHI."""
        # Perfect diversification: equal weights
        holdings = [
            PortfolioHolding(symbol="BTC", amount=Decimal("1"), current_price=Decimal("100")),
            PortfolioHolding(symbol="ETH", amount=Decimal("1"), current_price=Decimal("100")),
            PortfolioHolding(symbol="SOL", amount=Decimal("1"), current_price=Decimal("100")),
        ]
        
        div_score = calculate_diversification_score(holdings)
        
        # Should have high diversification (low HHI)
        self.assertGreater(float(div_score), 50)  # More than 50% diversified
    
    def test_portfolio_risk_score(self):
        """Test portfolio risk score."""
        holdings = [
            PortfolioHolding(symbol="BTC", amount=Decimal("1"), current_price=Decimal("100")),
        ]
        
        risk = calculate_portfolio_risk_score(holdings)
        
        # Single asset should have higher risk
        self.assertGreaterEqual(float(risk), 0)
        self.assertLessEqual(float(risk), 100)


if __name__ == '__main__':
    unittest.main()

