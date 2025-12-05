"""
Historical Service for Portfolio.
Handles portfolio snapshots, benchmark comparison, historical tracking.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import UUID
from shared.models import PortfolioSnapshot


class HistoricalService:
    """Service for historical portfolio tracking."""
    
    def create_snapshot(
        self,
        user_id: UUID,
        wallet_id: Optional[UUID],
        total_value: Decimal,
        total_cost: Decimal,
        total_profit_loss: Decimal,
        total_profit_loss_percent: Decimal,
        snapshot_date: date
    ) -> Dict:
        """
        Create a portfolio snapshot.
        
        Args:
            user_id: User ID
            wallet_id: Wallet ID (optional)
            total_value: Total portfolio value
            total_cost: Total cost basis
            total_profit_loss: Total profit/loss
            total_profit_loss_percent: Total profit/loss percentage
            snapshot_date: Date of snapshot
        
        Returns:
            Snapshot dict
        """
        return {
            'user_id': user_id,
            'wallet_id': wallet_id,
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_percent': total_profit_loss_percent,
            'snapshot_date': snapshot_date
        }
    
    def get_snapshots(
        self,
        snapshots: List[PortfolioSnapshot],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Get snapshots within date range.
        
        Args:
            snapshots: List of snapshot objects
            start_date: Start date (optional)
            end_date: End date (optional)
        
        Returns:
            List of snapshot dicts
        """
        filtered = snapshots
        
        if start_date:
            filtered = [s for s in filtered if s.snapshot_date >= start_date]
        
        if end_date:
            filtered = [s for s in filtered if s.snapshot_date <= end_date]
        
        # Sort by date
        filtered.sort(key=lambda x: x.snapshot_date)
        
        return [
            {
                'id': str(s.id),
                'user_id': str(s.user_id),
                'wallet_id': str(s.wallet_id) if s.wallet_id else None,
                'total_value': s.total_value,
                'total_cost': s.total_cost,
                'total_profit_loss': s.total_profit_loss,
                'total_profit_loss_percent': s.total_profit_loss_percent,
                'snapshot_date': s.snapshot_date.isoformat(),
                'created_at': s.created_at.isoformat()
            }
            for s in filtered
        ]
    
    def calculate_benchmark_comparison(
        self,
        portfolio_values: List[Decimal],
        portfolio_dates: List[date],
        benchmark_values: List[Decimal],
        benchmark_dates: List[date],
        benchmark_name: str
    ) -> Dict:
        """
        Compare portfolio performance with benchmark.
        
        Args:
            portfolio_values: List of portfolio values
            portfolio_dates: List of dates for portfolio values
            benchmark_values: List of benchmark values
            benchmark_dates: List of dates for benchmark values
            benchmark_name: Name of benchmark (e.g., 'BTC', 'ETH', 'SP500')
        
        Returns:
            Comparison dict with returns, outperformance, etc.
        """
        if not portfolio_values or not benchmark_values:
            return {
                'portfolio_return': Decimal('0'),
                'benchmark_return': Decimal('0'),
                'outperformance': Decimal('0'),
                'benchmark_name': benchmark_name,
                'timeframe': 'N/A',
                'comparison_data': []
            }
        
        # Calculate returns
        portfolio_start = portfolio_values[0]
        portfolio_end = portfolio_values[-1]
        portfolio_return = ((portfolio_end - portfolio_start) / portfolio_start * Decimal('100')) if portfolio_start > 0 else Decimal('0')
        
        benchmark_start = benchmark_values[0]
        benchmark_end = benchmark_values[-1]
        benchmark_return = ((benchmark_end - benchmark_start) / benchmark_start * Decimal('100')) if benchmark_start > 0 else Decimal('0')
        
        outperformance = portfolio_return - benchmark_return
        
        # Create comparison data (aligned by date)
        comparison_data = []
        min_length = min(len(portfolio_values), len(benchmark_values))
        
        for i in range(min_length):
            comparison_data.append({
                'date': portfolio_dates[i].isoformat() if i < len(portfolio_dates) else None,
                'portfolio_value': float(portfolio_values[i]),
                'benchmark_value': float(benchmark_values[i])
            })
        
        # Determine timeframe
        if portfolio_dates:
            days = (portfolio_dates[-1] - portfolio_dates[0]).days
            if days <= 7:
                timeframe = '1W'
            elif days <= 30:
                timeframe = '1M'
            elif days <= 90:
                timeframe = '3M'
            elif days <= 365:
                timeframe = '1Y'
            else:
                timeframe = f'{days}D'
        else:
            timeframe = 'N/A'
        
        return {
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'outperformance': outperformance,
            'benchmark_name': benchmark_name,
            'timeframe': timeframe,
            'comparison_data': comparison_data
        }
    
    def calculate_portfolio_returns(
        self,
        snapshots: List[PortfolioSnapshot]
    ) -> List[Decimal]:
        """
        Calculate portfolio returns from snapshots.
        
        Args:
            snapshots: List of snapshot objects (sorted by date)
        
        Returns:
            List of returns (as percentages)
        """
        returns = []
        
        if len(snapshots) < 2:
            return returns
        
        for i in range(1, len(snapshots)):
            prev_value = snapshots[i-1].total_value
            curr_value = snapshots[i].total_value
            
            if prev_value > 0:
                return_pct = ((curr_value - prev_value) / prev_value * Decimal('100'))
                returns.append(return_pct)
            else:
                returns.append(Decimal('0'))
        
        return returns

