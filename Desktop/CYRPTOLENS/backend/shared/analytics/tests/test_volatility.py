"""
Unit tests for Volatility indicator.
Following Indicator & Analytics Engine Specification exactly.
"""
import unittest
from decimal import Decimal
from ..indicators.volatility import calculate_volatility
from ..types import Candle


class TestVolatility(unittest.TestCase):
    """Test Volatility calculation with known test series."""
    
    def test_volatility_insufficient_data(self):
        """Test volatility with insufficient data."""
        closes = [Decimal("100")]
        
        result = calculate_volatility(closes)
        self.assertEqual(result["sigma"], Decimal(0))
        self.assertEqual(result["normalizedScore"], Decimal(0))
    
    def test_volatility_log_returns(self):
        """Test that volatility uses log returns."""
        # Create series with known returns
        closes = [
            Decimal("100"),
            Decimal("105"),  # +5%
            Decimal("110"),  # +4.76%
            Decimal("100"),  # -9.09%
        ]
        
        result = calculate_volatility(closes)
        
        # Should have non-zero volatility
        self.assertGreater(float(result["sigma"]), 0)
        self.assertGreaterEqual(float(result["normalizedScore"]), 0)
        self.assertLessEqual(float(result["normalizedScore"]), 1)
    
    def test_volatility_normalized_score(self):
        """Test normalized score is between 0-1."""
        closes = [Decimal(str(100 + i)) for i in range(20)]
        
        result = calculate_volatility(closes)
        
        self.assertGreaterEqual(float(result["normalizedScore"]), 0)
        self.assertLessEqual(float(result["normalizedScore"]), 1)


if __name__ == '__main__':
    unittest.main()

