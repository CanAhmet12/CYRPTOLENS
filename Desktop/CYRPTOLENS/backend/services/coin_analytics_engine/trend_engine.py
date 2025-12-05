"""
Trend Engine
Following Technical Specification for trend detection.
"""
from typing import List, Dict
from decimal import Decimal
from .technical_indicators import TechnicalIndicators


class TrendEngine:
    """Trend detection and analysis engine."""
    
    @staticmethod
    def detect_trend_direction(
        prices: List[Decimal],
        ema20: Decimal = None,
        ema50: Decimal = None,
        ema200: Decimal = None
    ) -> str:
        """
        Detect trend direction: bullish, bearish, or neutral.
        
        Based on:
        - EMA alignment (EMA20 > EMA50 > EMA200 = bullish)
        - Price position relative to EMAs
        - Momentum
        """
        if not prices or len(prices) < 2:
            return "neutral"
        
        current_price = prices[-1]
        
        # If EMAs provided, use them
        if ema20 and ema50 and ema200:
            # Bullish: EMAs aligned upward, price above EMAs
            if ema20 > ema50 > ema200 and current_price > ema20:
                return "bullish"
            # Bearish: EMAs aligned downward, price below EMAs
            elif ema20 < ema50 < ema200 and current_price < ema20:
                return "bearish"
            else:
                return "neutral"
        
        # Fallback: use price momentum
        if len(prices) >= 20:
            momentum = TechnicalIndicators.calculate_momentum(prices, 10)
            if momentum > 5:
                return "bullish"
            elif momentum < -5:
                return "bearish"
        
        return "neutral"
    
    @staticmethod
    def calculate_trend_strength(
        prices: List[Decimal],
        trend_direction: str,
        ema20: Decimal = None,
        ema50: Decimal = None,
        ema200: Decimal = None
    ) -> int:
        """
        Calculate trend strength (0-100).
        
        Based on:
        - EMA alignment
        - Momentum
        - Price consistency
        """
        if not prices or len(prices) < 2:
            return 0
        
        strength_factors = []
        
        # Factor 1: EMA alignment (if available)
        if ema20 and ema50 and ema200:
            if trend_direction == "bullish":
                # Check EMA alignment quality
                if ema20 > ema50 > ema200:
                    alignment_score = min(100, abs(float(ema20 - ema200)) / float(ema200) * 1000)
                    strength_factors.append(min(50, alignment_score))
            elif trend_direction == "bearish":
                if ema20 < ema50 < ema200:
                    alignment_score = min(100, abs(float(ema20 - ema200)) / float(ema200) * 1000)
                    strength_factors.append(min(50, alignment_score))
        
        # Factor 2: Momentum strength
        if len(prices) >= 20:
            momentum = TechnicalIndicators.calculate_momentum(prices, 10)
            momentum_score = min(50, abs(float(momentum)) * 2)
            strength_factors.append(momentum_score)
        
        # Factor 3: Price consistency (recent trend consistency)
        if len(prices) >= 10:
            recent_prices = prices[-10:]
            if trend_direction == "bullish":
                # Count how many prices are higher than previous
                increases = sum(1 for i in range(1, len(recent_prices)) 
                              if recent_prices[i] > recent_prices[i-1])
                consistency = (increases / len(recent_prices)) * 30
                strength_factors.append(consistency)
            elif trend_direction == "bearish":
                # Count how many prices are lower than previous
                decreases = sum(1 for i in range(1, len(recent_prices)) 
                              if recent_prices[i] < recent_prices[i-1])
                consistency = (decreases / len(recent_prices)) * 30
                strength_factors.append(consistency)
        
        # Calculate total strength (0-100)
        total_strength = sum(strength_factors)
        return min(100, max(0, int(total_strength)))
    
    @staticmethod
    def calculate_trend_score(
        prices: List[Decimal],
        ema20: Decimal = None,
        ema50: Decimal = None,
        ema200: Decimal = None
    ) -> Decimal:
        """
        Calculate overall trend score.
        Weighted composite of EMA alignment, momentum, and market condition.
        """
        trend_direction = TrendEngine.detect_trend_direction(
            prices, ema20, ema50, ema200
        )
        trend_strength = TrendEngine.calculate_trend_strength(
            prices, trend_direction, ema20, ema50, ema200
        )
        
        # Convert to score: -100 to +100
        # Bullish: positive, Bearish: negative, Neutral: near 0
        if trend_direction == "bullish":
            score = Decimal(trend_strength)
        elif trend_direction == "bearish":
            score = Decimal(-trend_strength)
        else:
            score = Decimal(0)
        
        return score
    
    @staticmethod
    def analyze_market_structure(prices: List[Decimal]) -> Dict:
        """
        Analyze market structure.
        Identifies higher highs, higher lows (uptrend) or lower highs, lower lows (downtrend).
        """
        if len(prices) < 20:
            return {
                "structure": "neutral",
                "higher_highs": False,
                "higher_lows": False,
                "lower_highs": False,
                "lower_lows": False
            }
        
        # Find peaks and troughs
        peaks = []
        troughs = []
        
        for i in range(5, len(prices) - 5):
            # Check for peak
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                is_peak = True
                for j in range(i-5, i+6):
                    if j != i and prices[j] >= prices[i]:
                        is_peak = False
                        break
                if is_peak:
                    peaks.append((i, prices[i]))
            
            # Check for trough
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                is_trough = True
                for j in range(i-5, i+6):
                    if j != i and prices[j] <= prices[i]:
                        is_trough = False
                        break
                if is_trough:
                    troughs.append((i, prices[i]))
        
        # Analyze structure
        higher_highs = False
        higher_lows = False
        lower_highs = False
        lower_lows = False
        
        if len(peaks) >= 2:
            recent_peaks = sorted(peaks[-2:], key=lambda x: x[0])
            if recent_peaks[1][1] > recent_peaks[0][1]:
                higher_highs = True
            elif recent_peaks[1][1] < recent_peaks[0][1]:
                lower_highs = True
        
        if len(troughs) >= 2:
            recent_troughs = sorted(troughs[-2:], key=lambda x: x[0])
            if recent_troughs[1][1] > recent_troughs[0][1]:
                higher_lows = True
            elif recent_troughs[1][1] < recent_troughs[0][1]:
                lower_lows = True
        
        # Determine structure
        if higher_highs and higher_lows:
            structure = "bullish"
        elif lower_highs and lower_lows:
            structure = "bearish"
        else:
            structure = "neutral"
        
        return {
            "structure": structure,
            "higher_highs": higher_highs,
            "higher_lows": higher_lows,
            "lower_highs": lower_highs,
            "lower_lows": lower_lows
        }

