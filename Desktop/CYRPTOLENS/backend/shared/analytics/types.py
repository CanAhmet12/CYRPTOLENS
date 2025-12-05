"""
Data structures for Analytics Engine.
Following Indicator & Analytics Engine Specification exactly.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class Candle:
    """
    Canonical candle type.
    Following Indicator & Analytics Engine Specification.
    
    timestamp: datetime object (will be converted to ms for calculations)
    open, high, low, close, volume: Decimal values
    """
    timestamp: int  # ms since epoch (for compatibility)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    
    @classmethod
    def from_provider_candle(cls, candle) -> 'Candle':
        """
        Convert from data provider Candle (with datetime timestamp).
        """
        from datetime import datetime
        
        if hasattr(candle, 'timestamp'):
            if isinstance(candle.timestamp, datetime):
                timestamp_ms = int(candle.timestamp.timestamp() * 1000)
            elif isinstance(candle.timestamp, (int, float)):
                timestamp_ms = int(candle.timestamp)
            else:
                timestamp_ms = 0
        else:
            timestamp_ms = 0
        
        return cls(
            timestamp=timestamp_ms,
            open=Decimal(str(candle.open)),
            high=Decimal(str(candle.high)),
            low=Decimal(str(candle.low)),
            close=Decimal(str(candle.close)),
            volume=Decimal(str(candle.volume)),
        )
    
    @classmethod
    def from_dataclass(cls, candle: 'Candle') -> 'Candle':
        """Create from another Candle (copy)."""
        return cls(
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume),
        }


def candles_to_closes(candles: List[Candle]) -> List[Decimal]:
    """Extract closing prices from candles array."""
    return [candle.close for candle in candles]


def candles_to_opens(candles: List[Candle]) -> List[Decimal]:
    """Extract opening prices from candles array."""
    return [candle.open for candle in candles]


def candles_to_highs(candles: List[Candle]) -> List[Decimal]:
    """Extract high prices from candles array."""
    return [candle.high for candle in candles]


def candles_to_lows(candles: List[Candle]) -> List[Decimal]:
    """Extract low prices from candles array."""
    return [candle.low for candle in candles]

