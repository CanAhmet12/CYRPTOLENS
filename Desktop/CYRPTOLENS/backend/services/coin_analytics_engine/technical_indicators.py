"""
Technical Indicator Calculations
Following Technical Specification formulas exactly.
"""
from typing import List
from decimal import Decimal
import math


class TechnicalIndicators:
    """Technical indicator calculation functions."""
    
    @staticmethod
    def calculate_ema(prices: List[Decimal], period: int) -> List[Decimal]:
        """
        Calculate Exponential Moving Average (EMA).
        
        EMA = Price(t) * k + EMA(y) * (1 – k)
        where k = 2 / (period + 1)
        """
        if not prices or period <= 0:
            return []
        
        if len(prices) < period:
            return []
        
        k = Decimal(2) / Decimal(period + 1)
        ema_values = []
        
        # Start with SMA for first value
        sma = sum(prices[:period]) / Decimal(period)
        ema_values.append(sma)
        
        # Calculate EMA for remaining values
        for i in range(period, len(prices)):
            ema = prices[i] * k + ema_values[-1] * (Decimal(1) - k)
            ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def calculate_rsi(prices: List[Decimal], period: int = 14) -> Decimal:
        """
        Calculate Relative Strength Index (RSI).
        
        Formula from Technical Specification:
        RS = Average Gain / Average Loss
        RSI = 100 - (100 / (1 + RS))
        """
        if len(prices) < period + 1:
            return Decimal(0)
        
        # Calculate price changes
        changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            changes.append(change)
        
        if len(changes) < period:
            return Decimal(0)
        
        # Separate gains and losses
        gains = [max(change, Decimal(0)) for change in changes[-period:]]
        losses = [abs(min(change, Decimal(0))) for change in changes[-period:]]
        
        # Calculate average gain and average loss
        avg_gain = sum(gains) / Decimal(period)
        avg_loss = sum(losses) / Decimal(period)
        
        if avg_loss == 0:
            return Decimal(100)  # All gains, no losses
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = Decimal(100) - (Decimal(100) / (Decimal(1) + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[Decimal],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> dict:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Formula from Technical Specification:
        MACD = EMA12 - EMA26
        Signal = EMA9 of MACD
        """
        if len(prices) < slow_period + signal_period:
            return {
                "macd": Decimal(0),
                "signal": Decimal(0),
                "histogram": Decimal(0)
            }
        
        # Calculate EMAs
        ema12 = TechnicalIndicators.calculate_ema(prices, fast_period)
        ema26 = TechnicalIndicators.calculate_ema(prices, slow_period)
        
        if not ema12 or not ema26:
            return {
                "macd": Decimal(0),
                "signal": Decimal(0),
                "histogram": Decimal(0)
            }
        
        # Calculate MACD line (difference between EMAs)
        # Align lengths
        min_len = min(len(ema12), len(ema26))
        macd_line = [
            ema12[-(min_len - i)] - ema26[-(min_len - i)]
            for i in range(min_len)
        ]
        
        if len(macd_line) < signal_period:
            return {
                "macd": Decimal(0),
                "signal": Decimal(0),
                "histogram": Decimal(0)
            }
        
        # Calculate Signal line (EMA9 of MACD)
        signal_line = TechnicalIndicators.calculate_ema(
            [Decimal(str(m)) for m in macd_line], signal_period
        )
        
        if not signal_line:
            return {
                "macd": Decimal(0),
                "signal": Decimal(0),
                "histogram": Decimal(0)
            }
        
        # Current MACD and Signal values
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        histogram = current_macd - current_signal
        
        return {
            "macd": Decimal(str(current_macd)),
            "signal": Decimal(str(current_signal)),
            "histogram": Decimal(str(histogram))
        }
    
    @staticmethod
    def calculate_volatility(prices: List[Decimal]) -> Decimal:
        """
        Calculate volatility score.
        
        Formula from Technical Specification:
        σ = sqrt( Σ(returns - mean)^2 / n )
        """
        if len(prices) < 2:
            return Decimal(0)
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                return_val = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(return_val)
        
        if not returns:
            return Decimal(0)
        
        # Calculate mean return
        mean_return = sum(returns) / Decimal(len(returns))
        
        # Calculate variance
        variance = sum([(r - mean_return) ** 2 for r in returns]) / Decimal(len(returns))
        
        # Calculate standard deviation (volatility)
        volatility = Decimal(math.sqrt(float(variance)))
        
        # Convert to percentage (0-100 scale)
        volatility_score = abs(volatility * Decimal(100))
        
        return min(volatility_score, Decimal(100))
    
    @staticmethod
    def calculate_momentum(prices: List[Decimal], period: int = 10) -> Decimal:
        """
        Calculate momentum score.
        Momentum = (Current Price - Price N periods ago) / Price N periods ago
        """
        if len(prices) < period + 1:
            return Decimal(0)
        
        current_price = prices[-1]
        past_price = prices[-(period + 1)]
        
        if past_price == 0:
            return Decimal(0)
        
        momentum = ((current_price - past_price) / past_price) * Decimal(100)
        
        return momentum
    
    @staticmethod
    def detect_support_resistance(
        prices: List[Decimal], window: int = 20
    ) -> dict:
        """
        Detect support and resistance levels.
        Uses local minima (support) and local maxima (resistance).
        """
        if len(prices) < window * 2:
            return {
                "support_levels": [],
                "resistance_levels": []
            }
        
        support_levels = []
        resistance_levels = []
        
        # Find local minima (support) and maxima (resistance)
        for i in range(window, len(prices) - window):
            # Check for local minimum (support)
            is_minimum = True
            for j in range(i - window, i + window + 1):
                if j != i and prices[j] < prices[i]:
                    is_minimum = False
                    break
            
            if is_minimum:
                support_levels.append(prices[i])
            
            # Check for local maximum (resistance)
            is_maximum = True
            for j in range(i - window, i + window + 1):
                if j != i and prices[j] > prices[i]:
                    is_maximum = False
                    break
            
            if is_maximum:
                resistance_levels.append(prices[i])
        
        # Remove duplicates and sort
        support_levels = sorted(list(set(support_levels)))
        resistance_levels = sorted(list(set(resistance_levels)), reverse=True)
        
        # Return top 5 support and resistance levels
        return {
            "support_levels": support_levels[:5],
            "resistance_levels": resistance_levels[:5]
        }

