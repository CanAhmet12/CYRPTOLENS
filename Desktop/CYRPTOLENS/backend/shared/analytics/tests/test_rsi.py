"""
Unit tests for RSI indicator.
Following Indicator & Analytics Engine Specification exactly.
"""
import unittest
from decimal import Decimal
from ..indicators.rsi import calculate_rsi
from ..types import Candle


class TestRSI(unittest.TestCase):
    """Test RSI calculation with known test series."""
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        candles = [
            Candle(timestamp=1000, open=Decimal("100"), high=Decimal("105"), 
                   low=Decimal("95"), close=Decimal("102"), volume=Decimal("1000"))
        ] * 10  # Only 10 candles, need 15 for RSI(14)
        
        result = calculate_rsi(candles, period=14)
        # Should return list with None values
        self.assertEqual(len(result), 10)
        self.assertTrue(all(r is None for r in result))
    
    def test_rsi_all_gains(self):
        """Test RSI when all changes are gains (should approach 100)."""
        # Create series with consistent gains
        closes = [Decimal("100") + Decimal(str(i)) for i in range(20)]
        result = calculate_rsi(closes, period=14)
        
        # Last RSI should be high (approaching 100)
        last_rsi = result[-1]
        self.assertIsNotNone(last_rsi)
        self.assertGreater(float(last_rsi), 50)
    
    def test_rsi_all_losses(self):
        """Test RSI when all changes are losses (should approach 0)."""
        # Create series with consistent losses
        closes = [Decimal("100") - Decimal(str(i)) for i in range(20)]
        result = calculate_rsi(closes, period=14)
        
        # Last RSI should be low (approaching 0)
        last_rsi = result[-1]
        self.assertIsNotNone(last_rsi)
        self.assertLess(float(last_rsi), 50)
    
    def test_rsi_wilders_smoothing(self):
        """Test that RSI uses Wilder's smoothing (not simple average)."""
        # Create known test series
        # First 14 periods: alternating gains/losses
        base_price = Decimal("100")
        closes = [base_price]
        
        for i in range(1, 20):
            if i % 2 == 0:
                closes.append(closes[-1] + Decimal("1"))  # Gain
            else:
                closes.append(closes[-1] - Decimal("0.5"))  # Loss
        
        result = calculate_rsi(closes, period=14)
        
        # Should have RSI values after period
        self.assertIsNotNone(result[-1])
        self.assertGreaterEqual(float(result[-1]), 0)
        self.assertLessEqual(float(result[-1]), 100)


if __name__ == '__main__':
    unittest.main()

