"""
Advanced Analytics Service for Portfolio.
Calculates Sharpe Ratio, Alpha/Beta, Correlation, Drawdown, Win Rate, etc.
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date, timedelta
import math
from shared.analytics.portfolio import PortfolioHolding


class AdvancedAnalyticsService:
    """Service for advanced portfolio analytics calculations."""
    
    # Risk-free rate (annual, can be configured)
    RISK_FREE_RATE = Decimal('0.02')  # 2% annual
    
    def calculate_sharpe_ratio(
        self,
        portfolio_returns: List[Decimal],
        risk_free_rate: Optional[Decimal] = None
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Calculate Sharpe Ratio.
        
        Formula: (Portfolio Return - Risk-Free Rate) / Portfolio Volatility
        
        Args:
            portfolio_returns: List of portfolio returns (as percentages)
            risk_free_rate: Annual risk-free rate (default: 2%)
        
        Returns:
            Tuple of (sharpe_ratio, portfolio_return, risk_free_rate, volatility)
        """
        if not portfolio_returns or len(portfolio_returns) < 2:
            return Decimal('0'), Decimal('0'), risk_free_rate or self.RISK_FREE_RATE, Decimal('0')
        
        risk_free = risk_free_rate or self.RISK_FREE_RATE
        
        # Calculate average return
        avg_return = sum(portfolio_returns) / Decimal(str(len(portfolio_returns)))
        
        # Calculate volatility (standard deviation)
        variance = sum([(r - avg_return) ** 2 for r in portfolio_returns]) / Decimal(str(len(portfolio_returns)))
        volatility = variance.sqrt() if variance > 0 else Decimal('0')
        
        # Annualize if needed (assuming daily returns)
        # For simplicity, we'll use the period returns as-is
        # In production, you'd annualize based on the timeframe
        
        # Calculate Sharpe Ratio
        if volatility > 0:
            sharpe_ratio = (avg_return - risk_free) / volatility
        else:
            sharpe_ratio = Decimal('0')
        
        return sharpe_ratio, avg_return, risk_free, volatility
    
    def calculate_alpha_beta(
        self,
        portfolio_returns: List[Decimal],
        benchmark_returns: List[Decimal]
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate Alpha and Beta.
        
        Beta: Covariance(portfolio, benchmark) / Variance(benchmark)
        Alpha: Portfolio Return - (Beta * Benchmark Return)
        
        Args:
            portfolio_returns: List of portfolio returns
            benchmark_returns: List of benchmark returns (same length)
        
        Returns:
            Tuple of (alpha, beta)
        """
        if (not portfolio_returns or not benchmark_returns or 
            len(portfolio_returns) != len(benchmark_returns) or 
            len(portfolio_returns) < 2):
            return Decimal('0'), Decimal('1')
        
        # Calculate averages
        avg_portfolio = sum(portfolio_returns) / Decimal(str(len(portfolio_returns)))
        avg_benchmark = sum(benchmark_returns) / Decimal(str(len(benchmark_returns)))
        
        # Calculate covariance
        covariance = sum([
            (portfolio_returns[i] - avg_portfolio) * (benchmark_returns[i] - avg_benchmark)
            for i in range(len(portfolio_returns))
        ]) / Decimal(str(len(portfolio_returns)))
        
        # Calculate benchmark variance
        benchmark_variance = sum([
            (benchmark_returns[i] - avg_benchmark) ** 2
            for i in range(len(benchmark_returns))
        ]) / Decimal(str(len(benchmark_returns)))
        
        # Calculate Beta
        if benchmark_variance > 0:
            beta = covariance / benchmark_variance
        else:
            beta = Decimal('1')
        
        # Calculate Alpha
        alpha = avg_portfolio - (beta * avg_benchmark)
        
        return alpha, beta
    
    def calculate_correlation_matrix(
        self,
        holdings: List[PortfolioHolding],
        price_history: Dict[str, List[Decimal]]
    ) -> Dict[str, Dict[str, Decimal]]:
        """
        Calculate correlation matrix between coins in portfolio.
        
        Args:
            holdings: List of portfolio holdings
            price_history: Dict mapping coin_symbol to list of prices
        
        Returns:
            Nested dict: {coin1: {coin2: correlation, ...}, ...}
        """
        correlation_matrix = {}
        symbols = [h.symbol for h in holdings]
        
        # Calculate returns for each coin
        returns_dict = {}
        for symbol in symbols:
            if symbol in price_history and len(price_history[symbol]) > 1:
                prices = price_history[symbol]
                returns = [
                    (prices[i] - prices[i-1]) / prices[i-1] * Decimal('100')
                    for i in range(1, len(prices))
                ]
                returns_dict[symbol] = returns
        
        # Calculate pairwise correlations
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = Decimal('1')
                elif symbol1 in returns_dict and symbol2 in returns_dict:
                    corr = self._calculate_correlation(
                        returns_dict[symbol1],
                        returns_dict[symbol2]
                    )
                    correlation_matrix[symbol1][symbol2] = corr
                else:
                    correlation_matrix[symbol1][symbol2] = Decimal('0')
        
        return correlation_matrix
    
    def _calculate_correlation(
        self,
        returns1: List[Decimal],
        returns2: List[Decimal]
    ) -> Decimal:
        """Calculate correlation coefficient between two return series."""
        if len(returns1) != len(returns2) or len(returns1) < 2:
            return Decimal('0')
        
        avg1 = sum(returns1) / Decimal(str(len(returns1)))
        avg2 = sum(returns2) / Decimal(str(len(returns2)))
        
        # Calculate covariance
        covariance = sum([
            (returns1[i] - avg1) * (returns2[i] - avg2)
            for i in range(len(returns1))
        ]) / Decimal(str(len(returns1)))
        
        # Calculate standard deviations
        var1 = sum([(r - avg1) ** 2 for r in returns1]) / Decimal(str(len(returns1)))
        var2 = sum([(r - avg2) ** 2 for r in returns2]) / Decimal(str(len(returns2)))
        
        std1 = var1.sqrt() if var1 > 0 else Decimal('0')
        std2 = var2.sqrt() if var2 > 0 else Decimal('0')
        
        # Calculate correlation
        if std1 > 0 and std2 > 0:
            correlation = covariance / (std1 * std2)
            # Clamp to [-1, 1]
            correlation = max(Decimal('-1'), min(Decimal('1'), correlation))
        else:
            correlation = Decimal('0')
        
        return correlation
    
    def calculate_drawdown(
        self,
        portfolio_values: List[Decimal]
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal, Optional[date]]:
        """
        Calculate drawdown metrics.
        
        Args:
            portfolio_values: List of portfolio values over time
        
        Returns:
            Tuple of (max_drawdown, max_drawdown_percent, current_drawdown, 
                     current_drawdown_percent, recovery_date)
        """
        if not portfolio_values or len(portfolio_values) < 2:
            return Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), None
        
        max_value = portfolio_values[0]
        max_drawdown = Decimal('0')
        max_drawdown_percent = Decimal('0')
        max_drawdown_index = 0
        
        # Track current drawdown
        current_peak = portfolio_values[0]
        current_drawdown = Decimal('0')
        current_drawdown_percent = Decimal('0')
        recovery_date = None
        
        for i, value in enumerate(portfolio_values):
            # Update peak
            if value > current_peak:
                current_peak = value
                if recovery_date is None and i > max_drawdown_index:
                    # Potential recovery
                    recovery_date = date.today() - timedelta(days=len(portfolio_values) - i)
            
            # Calculate drawdown from peak
            drawdown = current_peak - value
            drawdown_percent = (drawdown / current_peak * Decimal('100')) if current_peak > 0 else Decimal('0')
            
            # Update current drawdown
            current_drawdown = drawdown
            current_drawdown_percent = drawdown_percent
            
            # Track maximum drawdown
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent
                max_drawdown_index = i
                max_value = current_peak
        
        return (
            max_drawdown,
            max_drawdown_percent,
            current_drawdown,
            current_drawdown_percent,
            recovery_date
        )
    
    def calculate_win_rate(
        self,
        transactions: List[Dict]
    ) -> Tuple[Decimal, int, int, int]:
        """
        Calculate win rate from transactions.
        
        Args:
            transactions: List of transaction dicts with 'type', 'amount', 'price', 'profit_loss'
        
        Returns:
            Tuple of (win_rate, total_trades, winning_trades, losing_trades)
        """
        if not transactions:
            return Decimal('0'), 0, 0, 0
        
        # Filter completed trades (buy + sell pairs)
        # For simplicity, we'll use transactions with profit_loss field
        trades = [
            t for t in transactions
            if t.get('transaction_type') in ['buy', 'sell'] and 'profit_loss' in t
        ]
        
        if not trades:
            return Decimal('0'), 0, 0, 0
        
        winning_trades = sum(1 for t in trades if t.get('profit_loss', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('profit_loss', 0) < 0)
        break_even_trades = len(trades) - winning_trades - losing_trades
        
        total_trades = len(trades)
        win_rate = (Decimal(str(winning_trades)) / Decimal(str(total_trades)) * Decimal('100')) if total_trades > 0 else Decimal('0')
        
        return win_rate, total_trades, winning_trades, losing_trades
    
    def calculate_performance_attribution(
        self,
        holdings: List[PortfolioHolding],
        total_portfolio_value: Decimal,
        total_profit_loss: Decimal
    ) -> List[Dict[str, Decimal]]:
        """
        Calculate performance attribution by coin.
        
        Args:
            holdings: List of portfolio holdings
            total_portfolio_value: Total portfolio value
            total_profit_loss: Total profit/loss
        
        Returns:
            List of dicts with coin_symbol, contribution, contribution_percent, return_percent
        """
        attribution = []
        
        if total_portfolio_value == 0:
            return attribution
        
        for holding in holdings:
            coin_value = holding.amount * holding.current_price
            coin_cost = holding.amount * (holding.buy_price or Decimal('0'))
            coin_profit_loss = coin_value - coin_cost
            
            contribution = coin_profit_loss
            contribution_percent = (contribution / total_profit_loss * Decimal('100')) if total_profit_loss != 0 else Decimal('0')
            return_percent = ((holding.current_price - holding.buy_price) / holding.buy_price * Decimal('100')) if holding.buy_price > 0 else Decimal('0')
            
            attribution.append({
                'coin_symbol': holding.symbol,
                'contribution': contribution,
                'contribution_percent': contribution_percent,
                'return_percent': return_percent
            })
        
        # Sort by contribution (descending)
        attribution.sort(key=lambda x: x['contribution'], reverse=True)
        
        return attribution
    
    def calculate_sector_allocation(
        self,
        holdings: List[PortfolioHolding],
        coin_categories: Dict[str, str]
    ) -> List[Dict[str, any]]:
        """
        Calculate sector allocation.
        
        Args:
            holdings: List of portfolio holdings
            coin_categories: Dict mapping coin_symbol to sector/category
        
        Returns:
            List of dicts with sector, value, percentage, coins
        """
        sector_totals = {}
        
        for holding in holdings:
            sector = coin_categories.get(holding.symbol, 'Other')
            value = holding.amount * holding.current_price
            
            if sector not in sector_totals:
                sector_totals[sector] = {
                    'value': Decimal('0'),
                    'coins': []
                }
            
            sector_totals[sector]['value'] += value
            sector_totals[sector]['coins'].append(holding.symbol)
        
        # Calculate total value
        total_value = sum([h.amount * h.current_price for h in holdings])
        
        # Build response
        allocation = []
        for sector, data in sector_totals.items():
            percentage = (data['value'] / total_value * Decimal('100')) if total_value > 0 else Decimal('0')
            allocation.append({
                'sector': sector,
                'value': data['value'],
                'percentage': percentage,
                'coins': data['coins']
            })
        
        # Sort by value (descending)
        allocation.sort(key=lambda x: x['value'], reverse=True)
        
        return allocation

