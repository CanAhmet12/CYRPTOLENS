"""
Unit tests for MACD indicator.
Following Indicator & Analytics Engine Specification exactly.
"""
import unittest
from decimal import Decimal
from ..indicators.macd import calculate_macd
from ..types import Candle


class TestMACD(unittest.TestCase):
    """Test MACD calculation with known test series."""
    
    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data."""
        closes = [Decimal("100")] * 30  # Need at least 35 for MACD(12,26,9)
        
        result = calculate_macd(closes)
        self.assertEqual(len(result["macdLine"]), 0)
    
    def test_macd_basic_calculation(self):
        """Test basic MACD calculation."""
        # Create series with enough data
        closes = [Decimal(str(100 + i * 0.1)) for i in range(50)]
        
        result = calculate_macd(closes, fast_period=12, slow_period=26, signal_period=9)
        
        # Should have MACD line values
        self.assertGreater(len(result["macdLine"]), 0)
        self.assertGreater(len(result["signalLine"]), 0)
        self.assertGreater(len(result["histogram"]), 0)
    
    def test_macd_histogram_calculation(self):
        """Test that histogram = MACD - Signal."""
        closes = [Decimal(str(100 + i * 0.1)) for i in range(50)]
        
        result = calculate_macd(closes)
        
        # Find last non-None values
        macd_val = None
        signal_val = None
        hist_val = None
        
        for val in reversed(result["macdLine"]):
            if val is not None:
                macd_val = val
                break
        
        for val in reversed(result["signalLine"]):
            if val is not None:
                signal_val = val
                break
        
        for val in reversed(result["histogram"]):
            if val is not None:
                hist_val = val
                break
        
        if macd_val is not None and signal_val is not None and hist_val is not None:
            expected_hist = macd_val - signal_val
            self.assertAlmostEqual(float(hist_val), float(expected_hist), places=2)


if __name__ == '__main__':
    unittest.main()

