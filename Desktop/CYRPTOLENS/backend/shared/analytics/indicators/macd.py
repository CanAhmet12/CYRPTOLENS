"""
MACD (Moving Average Convergence Divergence) Indicator
Following Indicator & Analytics Engine Specification exactly.

Default parameters:
- Fast EMA: 12
- Slow EMA: 26
- Signal EMA: 9

Steps:
1. Compute EMA12 and EMA26
2. MACD line = EMA12 - EMA26
3. Signal line = EMA9(MACD)
4. Histogram = MACD - Signal
"""
from typing import List, Union, Dict
from decimal import Decimal
from ..types import Candle, candles_to_closes
from .ema import calculate_ema


def calculate_macd(
    data: Union[List[Candle], List[Decimal]],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, List[Decimal]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        data: List of Candle objects or List of closing prices (Decimal)
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal EMA period (default: 9)
    
    Returns:
        Dictionary with:
        - macdLine: List of MACD values
        - signalLine: List of Signal values
        - histogram: List of Histogram values
        
        All arrays aligned with input length (with None/empty for insufficient data).
    """
    # Extract closing prices if candles provided
    if data and isinstance(data[0], Candle):
        closes = candles_to_closes(data)
    else:
        closes = [Decimal(str(d)) if not isinstance(d, Decimal) else d for d in data]
    
    if not closes or len(closes) < slow_period + signal_period:
        return {
            "macdLine": [],
            "signalLine": [],
            "histogram": []
        }
    
    # Step 1: Compute EMA12 and EMA26
    ema12_list = calculate_ema(closes, fast_period)
    ema26_list = calculate_ema(closes, slow_period)
    
    if not ema12_list or not ema26_list:
        return {
            "macdLine": [],
            "signalLine": [],
            "histogram": []
        }
    
    # Calculate MACD line: EMA12 - EMA26
    # Both EMAs are lists aligned with closes array
    # EMA12[0] corresponds to closes[fast_period-1]
    # EMA26[0] corresponds to closes[slow_period-1]
    # MACD should start where EMA26 starts (slower EMA)
    
    macd_line = []
    
    # EMA12 has values starting from closes[fast_period-1]
    # EMA26 has values starting from closes[slow_period-1]
    # To align: EMA12 needs to skip (slow_period - fast_period) values
    offset = slow_period - fast_period
    
    # Calculate MACD for overlapping period
    # Start from where EMA26 starts
    for i in range(len(ema26_list)):
        ema12_idx = i + offset
        if ema12_idx < len(ema12_list):
            macd_value = ema12_list[ema12_idx] - ema26_list[i]
            macd_line.append(macd_value)
    
    if len(macd_line) < signal_period:
        return {
            "macdLine": [],
            "signalLine": [],
            "histogram": []
        }
    
    # Step 3: Calculate Signal line (EMA9 of MACD)
    signal_line = calculate_ema(macd_line, signal_period)
    
    if not signal_line:
        return {
            "macdLine": macd_line,
            "signalLine": [],
            "histogram": []
        }
    
    # Step 4: Calculate Histogram (MACD - Signal)
    # Align MACD and Signal for histogram calculation
    signal_offset = signal_period - 1
    histogram = []
    
    for i in range(signal_offset, len(macd_line)):
        signal_idx = i - signal_offset
        if signal_idx < len(signal_line):
            hist = macd_line[i] - signal_line[signal_idx]
            histogram.append(hist)
    
    # Pad arrays to align with input length
    # MACD line starts at slow_period-1 in closes array
    macd_padding = slow_period - 1
    macd_padded = [None] * macd_padding + macd_line
    
    # Signal line starts at (slow_period - 1) + (signal_period - 1)
    signal_padding = macd_padding + signal_offset
    signal_padded = [None] * signal_padding + signal_line
    
    # Histogram starts same as signal
    histogram_padded = [None] * signal_padding + histogram
    
    # Trim to match input length
    target_len = len(closes)
    
    def pad_to_length(arr, length):
        if len(arr) >= length:
            return arr[:length]
        else:
            return arr + [None] * (length - len(arr))
    
    return {
        "macdLine": pad_to_length(macd_padded, target_len),
        "signalLine": pad_to_length(signal_padded, target_len),
        "histogram": pad_to_length(histogram_padded, target_len)
    }

