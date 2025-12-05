"""
Tax Service for Portfolio.
Handles realized/unrealized gains, cost basis methods, tax year summaries.
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import UUID
from collections import deque
from shared.models import PortfolioTransaction, PortfolioTaxSettings


class TaxService:
    """Service for tax calculations and reporting."""
    
    def calculate_realized_unrealized(
        self,
        transactions: List[Dict],
        current_holdings: List[Dict],
        current_prices: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """
        Calculate realized and unrealized gains/losses.
        
        Args:
            transactions: List of transaction dicts
            current_holdings: List of current holdings with buy_price
            current_prices: Dict mapping coin_symbol to current price
        
        Returns:
            Dict with realized_gains, realized_losses, unrealized_gains, etc.
        """
        # Separate buy and sell transactions
        buy_transactions = [t for t in transactions if t.get('transaction_type') == 'buy']
        sell_transactions = [t for t in transactions if t.get('transaction_type') == 'sell']
        
        # Calculate realized gains/losses from sell transactions
        realized_gains = Decimal('0')
        realized_losses = Decimal('0')
        
        for sell_tx in sell_transactions:
            # Find corresponding buy transactions (FIFO method for now)
            # In production, this would use the cost basis method from settings
            profit_loss = sell_tx.get('profit_loss', Decimal('0'))
            if profit_loss > 0:
                realized_gains += profit_loss
            else:
                realized_losses += abs(profit_loss)
        
        # Calculate unrealized gains/losses from current holdings
        unrealized_gains = Decimal('0')
        unrealized_losses = Decimal('0')
        
        for holding in current_holdings:
            coin_symbol = holding.get('coin_symbol', '').upper()
            amount = Decimal(str(holding.get('amount', 0)))
            buy_price = Decimal(str(holding.get('buy_price', 0)))
            current_price = current_prices.get(coin_symbol, Decimal('0'))
            
            if current_price > 0 and buy_price > 0:
                profit_loss = (current_price - buy_price) * amount
                if profit_loss > 0:
                    unrealized_gains += profit_loss
                else:
                    unrealized_losses += abs(profit_loss)
        
        net_realized = realized_gains - realized_losses
        net_unrealized = unrealized_gains - unrealized_losses
        total_gains = realized_gains + unrealized_gains
        total_losses = realized_losses + unrealized_losses
        net_total = net_realized + net_unrealized
        
        return {
            'realized_gains': realized_gains,
            'realized_losses': realized_losses,
            'net_realized': net_realized,
            'unrealized_gains': unrealized_gains,
            'unrealized_losses': unrealized_losses,
            'net_unrealized': net_unrealized,
            'total_gains': total_gains,
            'total_losses': total_losses,
            'net_total': net_total
        }
    
    def calculate_cost_basis_fifo(
        self,
        buy_transactions: List[Dict],
        sell_amount: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate cost basis using FIFO (First In, First Out) method.
        
        Args:
            buy_transactions: List of buy transactions (sorted by date)
            sell_amount: Amount being sold
        
        Returns:
            Tuple of (cost_basis, remaining_buy_transactions)
        """
        cost_basis = Decimal('0')
        remaining_amount = sell_amount
        remaining_transactions = []
        
        for buy_tx in sorted(buy_transactions, key=lambda x: x.get('transaction_date', datetime.min)):
            buy_amount = Decimal(str(buy_tx.get('amount', 0)))
            buy_price = Decimal(str(buy_tx.get('price', 0)))
            
            if remaining_amount <= 0:
                remaining_transactions.append(buy_tx)
                continue
            
            if buy_amount <= remaining_amount:
                # Use entire buy transaction
                cost_basis += buy_amount * buy_price
                remaining_amount -= buy_amount
            else:
                # Use partial buy transaction
                cost_basis += remaining_amount * buy_price
                # Update buy transaction with remaining amount
                updated_tx = buy_tx.copy()
                updated_tx['amount'] = float(buy_amount - remaining_amount)
                remaining_transactions.append(updated_tx)
                remaining_amount = Decimal('0')
        
        return cost_basis, remaining_transactions
    
    def calculate_cost_basis_lifo(
        self,
        buy_transactions: List[Dict],
        sell_amount: Decimal
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculate cost basis using LIFO (Last In, First Out) method.
        
        Args:
            buy_transactions: List of buy transactions (sorted by date)
            sell_amount: Amount being sold
        
        Returns:
            Tuple of (cost_basis, remaining_buy_transactions)
        """
        cost_basis = Decimal('0')
        remaining_amount = sell_amount
        remaining_transactions = []
        
        # Sort in reverse order (newest first)
        for buy_tx in sorted(buy_transactions, key=lambda x: x.get('transaction_date', datetime.max), reverse=True):
            buy_amount = Decimal(str(buy_tx.get('amount', 0)))
            buy_price = Decimal(str(buy_tx.get('price', 0)))
            
            if remaining_amount <= 0:
                remaining_transactions.insert(0, buy_tx)  # Keep original order
                continue
            
            if buy_amount <= remaining_amount:
                # Use entire buy transaction
                cost_basis += buy_amount * buy_price
                remaining_amount -= buy_amount
            else:
                # Use partial buy transaction
                cost_basis += remaining_amount * buy_price
                # Update buy transaction with remaining amount
                updated_tx = buy_tx.copy()
                updated_tx['amount'] = float(buy_amount - remaining_amount)
                remaining_transactions.insert(0, updated_tx)  # Keep original order
                remaining_amount = Decimal('0')
        
        return cost_basis, remaining_transactions
    
    def calculate_cost_basis_avg(
        self,
        buy_transactions: List[Dict]
    ) -> Decimal:
        """
        Calculate average cost basis.
        
        Args:
            buy_transactions: List of buy transactions
        
        Returns:
            Average cost basis per unit
        """
        if not buy_transactions:
            return Decimal('0')
        
        total_cost = Decimal('0')
        total_amount = Decimal('0')
        
        for buy_tx in buy_transactions:
            amount = Decimal(str(buy_tx.get('amount', 0)))
            price = Decimal(str(buy_tx.get('price', 0)))
            total_cost += amount * price
            total_amount += amount
        
        if total_amount > 0:
            return total_cost / total_amount
        return Decimal('0')
    
    def get_tax_year_summary(
        self,
        transactions: List[Dict],
        tax_year: int,
        tax_year_start_month: int = 1,
        tax_year_start_day: int = 1
    ) -> Dict[str, any]:
        """
        Get tax year summary.
        
        Args:
            transactions: List of all transactions
            tax_year: Tax year (e.g., 2024)
            tax_year_start_month: Month when tax year starts (1-12)
            tax_year_start_day: Day when tax year starts (1-31)
        
        Returns:
            Dict with year, realized_gains, realized_losses, etc.
        """
        # Calculate tax year date range
        year_start = date(tax_year, tax_year_start_month, tax_year_start_day)
        if tax_year_start_month == 1 and tax_year_start_day == 1:
            year_end = date(tax_year + 1, 1, 1) - timedelta(days=1)
        else:
            year_end = date(tax_year + 1, tax_year_start_month, tax_year_start_day) - timedelta(days=1)
        
        # Filter transactions for this tax year
        year_transactions = []
        for t in transactions:
            tx_date = t.get('transaction_date')
            if tx_date is None:
                continue
            if isinstance(tx_date, datetime):
                tx_date_only = tx_date.date()
            elif isinstance(tx_date, date):
                tx_date_only = tx_date
            else:
                continue
            if year_start <= tx_date_only <= year_end:
                year_transactions.append(t)
        
        # Separate buy and sell
        buy_transactions = [t for t in year_transactions if t.get('transaction_type') == 'buy']
        sell_transactions = [t for t in year_transactions if t.get('transaction_type') == 'sell']
        
        # Calculate realized gains/losses
        realized_gains = Decimal('0')
        realized_losses = Decimal('0')
        
        for sell_tx in sell_transactions:
            profit_loss = Decimal(str(sell_tx.get('profit_loss', 0)))
            if profit_loss > 0:
                realized_gains += profit_loss
            else:
                realized_losses += abs(profit_loss)
        
        net_capital_gains = realized_gains - realized_losses
        
        return {
            'year': tax_year,
            'realized_gains': realized_gains,
            'realized_losses': realized_losses,
            'net_capital_gains': net_capital_gains,
            'transactions_count': len(year_transactions),
            'buy_transactions': len(buy_transactions),
            'sell_transactions': len(sell_transactions)
        }

