"""
Volatility Indicator
Following Indicator & Analytics Engine Specification exactly.

Volatility is based on standard deviation of log returns.

Steps:
1. Compute log returns: r[i] = ln(close[i] / close[i-1])
2. Compute mean of returns: mean = sum(r) / N
3. Compute variance: variance = sum((r[i] - mean)^2) / N
4. Standard deviation: sigma = sqrt(variance)
5. Normalized score: min(sigma / threshold, 1) where threshold is 0.05-0.10
"""
from typing import List, Union, Dict
from decimal import Decimal
import math
from ..types import Candle, candles_to_closes


def calculate_volatility(
    data: Union[List[Candle], List[Decimal]],
    threshold: Decimal = Decimal("0.05")
) -> Dict[str, Decimal]:
    """
    Calculate volatility based on standard deviation of log returns.
    
    Args:
        data: List of Candle objects or List of closing prices (Decimal)
        threshold: Tuning parameter for normalized score (default: 0.05)
    
    Returns:
        Dictionary with:
        - sigma: Standard deviation (volatility)
        - normalizedScore: Normalized score (0-1)
    """
    # Extract closing prices if candles provided
    if data and isinstance(data[0], Candle):
        closes = candles_to_closes(data)
    else:
        closes = [Decimal(str(d)) if not isinstance(d, Decimal) else d for d in data]
    
    if len(closes) < 2:
        return {
            "sigma": Decimal(0),
            "normalizedScore": Decimal(0)
        }
    
    # Step 1: Compute log returns
    log_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            ratio = closes[i] / closes[i - 1]
            # Use Decimal for precision, but need to convert to float for log
            log_return = Decimal(str(math.log(float(ratio))))
            log_returns.append(log_return)
    
    if not log_returns:
        return {
            "sigma": Decimal(0),
            "normalizedScore": Decimal(0)
        }
    
    # Step 2: Compute mean of returns
    mean_return = sum(log_returns) / Decimal(len(log_returns))
    
    # Step 3: Compute variance
    variance = sum([(r - mean_return) ** 2 for r in log_returns]) / Decimal(len(log_returns))
    
    # Step 4: Standard deviation (volatility)
    sigma = Decimal(str(math.sqrt(float(variance))))
    
    # Step 5: Normalized score (0-1)
    if threshold == 0:
        normalized_score = Decimal(1)  # Avoid division by zero
    else:
        normalized_score = min(sigma / threshold, Decimal(1))
    
    return {
        "sigma": sigma,
        "normalizedScore": normalized_score
    }

