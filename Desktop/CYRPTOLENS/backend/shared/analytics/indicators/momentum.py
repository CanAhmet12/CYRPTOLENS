"""
Momentum Score Indicator
Following Indicator & Analytics Engine Specification exactly.

Momentum measures the speed and direction of price changes.

Implementation:
- Compute percentage change over N periods (e.g. last 10 candles):
  momentumRaw = (close[last] - close[last-N]) / close[last-N]
- Map to 0-100 scale:
  momentumScore = clamp( (momentumRaw * factor) + 50, 0, 100 )
  Where factor scales typical % moves into usable range (e.g. 500).
"""
from typing import List, Union, Dict
from decimal import Decimal
from ..types import Candle, candles_to_closes


def calculate_momentum(
    data: Union[List[Candle], List[Decimal]],
    period: int = 10,
    factor: Decimal = Decimal("500")
) -> Dict[str, Union[Decimal, str]]:
    """
    Calculate momentum score.
    
    Args:
        data: List of Candle objects or List of closing prices (Decimal)
        period: Number of periods to look back (default: 10)
        factor: Scaling factor for normalization (default: 500)
    
    Returns:
        Dictionary with:
        - momentumScore: 0-100 score
        - momentumLabel: "weak", "moderate", "strong"
    """
    # Extract closing prices if candles provided
    if data and isinstance(data[0], Candle):
        closes = candles_to_closes(data)
    else:
        closes = [Decimal(str(d)) if not isinstance(d, Decimal) else d for d in data]
    
    if len(closes) < period + 1:
        return {
            "momentumScore": Decimal(50),  # Neutral
            "momentumLabel": "weak"
        }
    
    # Get current and past prices
    current_price = closes[-1]
    past_price = closes[-(period + 1)]
    
    if past_price == 0:
        return {
            "momentumScore": Decimal(50),
            "momentumLabel": "weak"
        }
    
    # Calculate raw momentum (percentage change)
    momentum_raw = (current_price - past_price) / past_price
    
    # Map to 0-100 scale
    momentum_score = (momentum_raw * factor) + Decimal(50)
    
    # Clamp between 0 and 100
    momentum_score = max(Decimal(0), min(momentum_score, Decimal(100)))
    
    # Determine label
    if momentum_score >= 70:
        label = "strong"
    elif momentum_score <= 30:
        label = "weak"
    else:
        label = "moderate"
    
    return {
        "momentumScore": momentum_score,
        "momentumLabel": label
    }

