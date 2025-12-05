"""
RSI (Relative Strength Index) Indicator
Following Indicator & Analytics Engine Specification exactly.

Default period: 14

Formula:
1. Compute gains and losses:
   gain[i] = max(close[i] - close[i-1], 0)
   loss[i] = max(close[i-1] - close[i], 0)

2. Compute initial average gain and loss over first 14 periods:
   avgGain = sum(gain[1..14]) / 14
   avgLoss = sum(loss[1..14]) / 14

3. For each next value, use Wilder's smoothing:
   avgGain = (prevAvgGain * (period - 1) + currentGain) / period
   avgLoss = (prevAvgLoss * (period - 1) + currentLoss) / period

4. RS = avgGain / avgLoss  (if avgLoss == 0 → RSI = 100)
   RSI = 100 - (100 / (1 + RS))
"""
from typing import List, Union, Optional
from decimal import Decimal
from ..types import Candle, candles_to_closes


def calculate_rsi(
    data: Union[List[Candle], List[Decimal]],
    period: int = 14
) -> List[Optional[Decimal]]:
    """
    Calculate RSI (Relative Strength Index) using Wilder's smoothing.
    
    Args:
        data: List of Candle objects or List of closing prices (Decimal)
        period: RSI period (default: 14)
    
    Returns:
        List of RSI values aligned with input length.
        First (period) values will be None until enough data exists.
        Following specification exactly with Wilder's smoothing.
    """
    # Extract closing prices if candles provided
    if data and isinstance(data[0], Candle):
        closes = candles_to_closes(data)
    else:
        closes = [Decimal(str(d)) if not isinstance(d, Decimal) else d for d in data]
    
    if not closes or period <= 0:
        return []
    
    if len(closes) < period + 1:
        return [None] * len(closes)
    
    # Initialize result array with None for first period values
    rsi_values = [None] * period
    
    # Step 1: Compute gains and losses
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, Decimal(0)))
        losses.append(max(-change, Decimal(0)))
    
    # Step 2: Compute initial average gain and loss over first period
    if len(gains) < period:
        return [None] * len(closes)
    
    avg_gain = sum(gains[:period]) / Decimal(period)
    avg_loss = sum(losses[:period]) / Decimal(period)
    
    # Calculate first RSI value
    if avg_loss == 0:
        first_rsi = Decimal(100)
    else:
        rs = avg_gain / avg_loss
        first_rsi = Decimal(100) - (Decimal(100) / (Decimal(1) + rs))
    
    rsi_values.append(first_rsi)
    
    # Step 3: For each next value, use Wilder's smoothing
    for i in range(period, len(gains)):
        current_gain = gains[i]
        current_loss = losses[i]
        
        # Wilder's smoothing formula
        avg_gain = (avg_gain * Decimal(period - 1) + current_gain) / Decimal(period)
        avg_loss = (avg_loss * Decimal(period - 1) + current_loss) / Decimal(period)
        
        # Step 4: Calculate RS and RSI
        if avg_loss == 0:
            rsi = Decimal(100)
        else:
            rs = avg_gain / avg_loss
            rsi = Decimal(100) - (Decimal(100) / (Decimal(1) + rs))
        
        rsi_values.append(rsi)
    
    return rsi_values

