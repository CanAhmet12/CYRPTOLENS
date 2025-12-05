"""
EMA (Exponential Moving Average) Indicator
Following Indicator & Analytics Engine Specification exactly.

Formula:
- multiplier = 2 / (period + 1)
- EMA(today) = (close(today) - EMA(yesterday)) * multiplier + EMA(yesterday)
- Initial EMA seed: simple moving average of first N candles.
"""
from typing import List, Union
from decimal import Decimal
from ..types import Candle, candles_to_closes


def calculate_ema(
    data: Union[List[Candle], List[Decimal]],
    period: int
) -> List[Decimal]:
    """
    Calculate Exponential Moving Average (EMA).
    
    Args:
        data: List of Candle objects or List of closing prices (Decimal)
        period: EMA period (e.g., 20, 50, 200)
    
    Returns:
        List of EMA values aligned with input length.
        First (period-1) values will be None/empty until enough data exists.
        Returns empty list if insufficient data.
    
    Following specification:
    - multiplier = 2 / (period + 1)
    - EMA(today) = (close(today) - EMA(yesterday)) * multiplier + EMA(yesterday)
    - Initial seed: SMA of first N candles
    """
    # Extract closing prices if candles provided
    if data and isinstance(data[0], Candle):
        closes = candles_to_closes(data)
    else:
        closes = [Decimal(str(d)) for d in data]
    
    if not closes or period <= 0:
        return []
    
    if len(closes) < period:
        return []
    
    # Calculate multiplier
    multiplier = Decimal(2) / Decimal(period + 1)
    
    # Initialize with SMA of first period values
    sma = sum(closes[:period]) / Decimal(period)
    ema_values = [sma]
    
    # Calculate EMA for remaining values using Wilder's formula
    for i in range(period, len(closes)):
        ema = (closes[i] - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema)
    
    return ema_values

