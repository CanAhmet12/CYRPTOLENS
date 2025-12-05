"""
Unit tests for EMA indicator.
Following Indicator & Analytics Engine Specification exactly.
"""
import unittest
from decimal import Decimal
from ..indicators.ema import calculate_ema
from ..types import Candle


class TestEMA(unittest.TestCase):
    """Test EMA calculation with known test series."""
    
    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        closes = [Decimal("100")] * 10  # Only 10 values, need 20 for EMA20
        
        result = calculate_ema(closes, period=20)
        self.assertEqual(len(result), 0)
    
    def test_ema_single_value(self):
        """Test EMA with exact period length."""
        closes = [Decimal("100")] * 20
        
        result = calculate_ema(closes, period=20)
        # Should have 1 value (SMA of first 20)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], Decimal("100"))
    
    def test_ema_initial_sma(self):
        """Test that EMA starts with SMA."""
        closes = [Decimal(str(100 + i)) for i in range(25)]  # 25 values for EMA20
        
        result = calculate_ema(closes, period=20)
        
        # First value should be SMA of first 20
        expected_sma = sum(closes[:20]) / Decimal(20)
        self.assertEqual(result[0], expected_sma)
    
    def test_ema_smoothing(self):
        """Test EMA smoothing formula."""
        # Create known series
        closes = [Decimal("100")] * 25
        
        result = calculate_ema(closes, period=20)
        
        # All values should be 100 (no change)
        self.assertTrue(all(v == Decimal("100") for v in result))
    
    def test_ema_with_candles(self):
        """Test EMA with Candle objects."""
        candles = [
            Candle(timestamp=1000 + i, open=Decimal("100"), high=Decimal("105"),
                   low=Decimal("95"), close=Decimal(str(100 + i)), volume=Decimal("1000"))
            for i in range(25)
        ]
        
        result = calculate_ema(candles, period=20)
        
        # Should have 6 values (25 - 20 + 1)
        self.assertEqual(len(result), 6)
        self.assertIsInstance(result[0], Decimal)


if __name__ == '__main__':
    unittest.main()

