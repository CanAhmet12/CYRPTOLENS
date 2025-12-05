"""
DCA (Dollar Cost Averaging) Service for Portfolio.
Handles DCA plans, execution tracking, average cost calculation.
"""
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import UUID
from shared.models import PortfolioDCAPlan, PortfolioDCAExecution


class DCAService:
    """Service for DCA strategy management."""
    
    def calculate_average_cost(
        self,
        executions: List[PortfolioDCAExecution]
    ) -> Decimal:
        """
        Calculate average cost from DCA executions.
        
        Args:
            executions: List of DCA execution objects
        
        Returns:
            Average cost per unit
        """
        if not executions:
            return Decimal('0')
        
        total_cost = Decimal('0')
        total_amount = Decimal('0')
        
        for execution in executions:
            total_cost += execution.total_cost
            total_amount += execution.amount
        
        if total_amount > 0:
            return total_cost / total_amount
        return Decimal('0')
    
    def should_execute_dca(
        self,
        dca_plan: PortfolioDCAPlan,
        last_execution_date: Optional[date] = None
    ) -> bool:
        """
        Check if DCA plan should be executed today.
        
        Args:
            dca_plan: DCA plan object
            last_execution_date: Date of last execution (optional)
        
        Returns:
            True if should execute
        """
        if not dca_plan.is_active:
            return False
        
        today = date.today()
        
        # Check if plan has started
        if today < dca_plan.start_date:
            return False
        
        # Check if plan has ended
        if dca_plan.end_date and today > dca_plan.end_date:
            return False
        
        # Check period type
        if last_execution_date:
            days_since_last = (today - last_execution_date).days
            
            if dca_plan.period_type == 'daily' and days_since_last >= 1:
                return True
            elif dca_plan.period_type == 'weekly' and days_since_last >= 7:
                return True
            elif dca_plan.period_type == 'monthly' and days_since_last >= 30:
                return True
        else:
            # First execution
            if dca_plan.period_type == 'daily':
                return today >= dca_plan.start_date
            elif dca_plan.period_type == 'weekly':
                # Execute on same day of week
                return today >= dca_plan.start_date and today.weekday() == dca_plan.start_date.weekday()
            elif dca_plan.period_type == 'monthly':
                # Execute on same day of month
                return today >= dca_plan.start_date and today.day == dca_plan.start_date.day
        
        return False
    
    def get_next_execution_date(
        self,
        dca_plan: PortfolioDCAPlan,
        last_execution_date: Optional[date] = None
    ) -> Optional[date]:
        """
        Get next execution date for DCA plan.
        
        Args:
            dca_plan: DCA plan object
            last_execution_date: Date of last execution (optional)
        
        Returns:
            Next execution date or None
        """
        if not dca_plan.is_active:
            return None
        
        base_date = last_execution_date or dca_plan.start_date
        today = date.today()
        
        if dca_plan.period_type == 'daily':
            next_date = base_date + timedelta(days=1)
        elif dca_plan.period_type == 'weekly':
            next_date = base_date + timedelta(weeks=1)
        elif dca_plan.period_type == 'monthly':
            # Add approximately one month
            if base_date.month == 12:
                next_date = date(base_date.year + 1, 1, base_date.day)
            else:
                next_date = date(base_date.year, base_date.month + 1, base_date.day)
        else:
            return None
        
        # Check if next date is before end date
        if dca_plan.end_date and next_date > dca_plan.end_date:
            return None
        
        return next_date if next_date >= today else None
    
    def calculate_total_invested(
        self,
        executions: List[PortfolioDCAExecution]
    ) -> Decimal:
        """
        Calculate total amount invested through DCA.
        
        Args:
            executions: List of DCA execution objects
        
        Returns:
            Total invested amount
        """
        return sum([execution.total_cost for execution in executions])
    
    def calculate_total_acquired(
        self,
        executions: List[PortfolioDCAExecution]
    ) -> Decimal:
        """
        Calculate total amount of coins acquired through DCA.
        
        Args:
            executions: List of DCA execution objects
        
        Returns:
            Total amount acquired
        """
        return sum([execution.amount for execution in executions])

