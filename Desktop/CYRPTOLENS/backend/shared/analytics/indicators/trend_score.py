"""
Trend Score Indicator
Following Indicator & Analytics Engine Specification exactly.

TrendScore is a synthetic metric combining:
- EMA alignment
- MACD state
- RSI region
- Price vs EMA200

Heuristic:
1. Start baseScore = 50
2. If price > EMA200 → +10, else -10
3. If EMA20 > EMA50 > EMA200 → +10 (strong uptrend)
4. If EMA20 < EMA50 < EMA200 → -10 (strong downtrend)
5. If MACD histogram rising → +5, falling → -5
6. If RSI between 45-60 → +5 (healthy)
7. If RSI > 70 → -5 (overbought risk)
8. If RSI < 30 → -5 (oversold risk)

Clamp final result between 0 and 100.
"""
from typing import List, Union, Dict, Optional
from decimal import Decimal
from ..types import Candle, candles_to_closes
from .ema import calculate_ema
from .rsi import calculate_rsi
from .macd import calculate_macd


def calculate_trend_score(
    data: Union[List[Candle], List[Decimal]],
    ema20: Optional[Decimal] = None,
    ema50: Optional[Decimal] = None,
    ema200: Optional[Decimal] = None,
    macd_histogram: Optional[Decimal] = None,
    rsi: Optional[Decimal] = None
) -> Dict[str, Union[Decimal, str]]:
    """
    Calculate Trend Score using heuristic approach.
    
    Args:
        data: List of Candle objects or List of closing prices (Decimal)
        ema20: Pre-calculated EMA20 value (optional, will calculate if not provided)
        ema50: Pre-calculated EMA50 value (optional, will calculate if not provided)
        ema200: Pre-calculated EMA200 value (optional, will calculate if not provided)
        macd_histogram: Pre-calculated MACD histogram value (optional, will calculate if not provided)
        rsi: Pre-calculated RSI value (optional, will calculate if not provided)
    
    Returns:
        Dictionary with:
        - trendScore: 0-100 score
        - trendLabel: "bullish" | "bearish" | "neutral"
    """
    # Extract closing prices if candles provided
    if data and isinstance(data[0], Candle):
        closes = candles_to_closes(data)
    else:
        closes = [Decimal(str(d)) if not isinstance(d, Decimal) else d for d in data]
    
    if not closes or len(closes) < 200:
        return {
            "trendScore": Decimal(50),
            "trendLabel": "neutral"
        }
    
    current_price = closes[-1]
    
    # Calculate indicators if not provided
    if ema20 is None or ema50 is None or ema200 is None:
        ema20_list = calculate_ema(closes, 20)
        ema50_list = calculate_ema(closes, 50)
        ema200_list = calculate_ema(closes, 200)
        
        ema20 = ema20_list[-1] if ema20_list else current_price
        ema50 = ema50_list[-1] if ema50_list else current_price
        ema200 = ema200_list[-1] if ema200_list else current_price
    
    if rsi is None:
        rsi_list = calculate_rsi(closes)
        rsi = rsi_list[-1] if rsi_list and rsi_list[-1] is not None else Decimal(50)
    
    if macd_histogram is None:
        macd_data = calculate_macd(closes)
        hist_list = macd_data.get("histogram", [])
        if hist_list:
            # Get last non-None histogram value
            for h in reversed(hist_list):
                if h is not None:
                    macd_histogram = h
                    break
            if macd_histogram is None:
                macd_histogram = Decimal(0)
        else:
            macd_histogram = Decimal(0)
    
    # Start with base score
    score = Decimal(50)
    
    # Rule 2: Price vs EMA200
    if current_price > ema200:
        score += Decimal(10)
    else:
        score -= Decimal(10)
    
    # Rule 3 & 4: EMA alignment
    if ema20 > ema50 > ema200:
        score += Decimal(10)  # Strong uptrend
    elif ema20 < ema50 < ema200:
        score -= Decimal(10)  # Strong downtrend
    
    # Rule 5: MACD histogram
    if macd_histogram > 0:
        score += Decimal(5)  # Rising
    elif macd_histogram < 0:
        score -= Decimal(5)  # Falling
    
    # Rule 6, 7, 8: RSI region
    if Decimal(45) <= rsi <= Decimal(60):
        score += Decimal(5)  # Healthy
    elif rsi > Decimal(70):
        score -= Decimal(5)  # Overbought risk
    elif rsi < Decimal(30):
        score -= Decimal(5)  # Oversold risk
    
    # Clamp between 0 and 100
    score = max(Decimal(0), min(score, Decimal(100)))
    
    # Determine label
    if score >= 65:
        label = "bullish"
    elif score <= 35:
        label = "bearish"
    else:
        label = "neutral"
    
    return {
        "trendScore": score,
        "trendLabel": label
    }

