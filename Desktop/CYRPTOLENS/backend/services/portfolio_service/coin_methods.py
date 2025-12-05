"""
Coin-Specific Portfolio Methods
Additional methods for coin detail page portfolio features
"""
from typing import List, Dict, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from uuid import UUID


def add_coin_methods_to_service(service_class):
    """Add coin-specific methods to PortfolioService."""
    
    async def get_coin_position(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        wallet_id: Optional[UUID] = None
    ) -> Dict:
        """Get portfolio position for a specific coin."""
        try:
            # Get portfolio items for this coin
            items = self.db_service.get_user_portfolio(db, user_id, wallet_id)
            coin_items = [item for item in items if item.coin_symbol.upper() == coin_symbol.upper()]
            
            if not coin_items:
                return {
                    "coin_symbol": coin_symbol.upper(),
                    "total_amount": Decimal("0"),
                    "average_cost": Decimal("0"),
                    "current_price": Decimal("0"),
                    "total_value": Decimal("0"),
                    "unrealized_gain": Decimal("0"),
                    "unrealized_gain_percent": Decimal("0"),
                    "transactions_count": 0,
                }
            
            # Get current price
            coin_symbols = [coin_symbol.upper()]
            price_data_map = await self.repository.get_portfolio_data(coin_symbols)
            current_price = Decimal("0")
            if coin_symbol.upper() in price_data_map:
                current_price = price_data_map[coin_symbol.upper()].price
            
            # Calculate totals
            total_amount = sum(item.amount for item in coin_items)
            total_cost = sum(item.amount * item.purchase_price for item in coin_items)
            average_cost = total_cost / total_amount if total_amount > 0 else Decimal("0")
            total_value = total_amount * current_price
            unrealized_gain = total_value - total_cost
            unrealized_gain_percent = (unrealized_gain / total_cost * 100) if total_cost > 0 else Decimal("0")
            
            # Get transaction count
            transactions = self.db_service.get_user_transactions(db, user_id, wallet_id, limit=1000)
            coin_transactions = [t for t in transactions if t.coin_symbol.upper() == coin_symbol.upper()]
            
            return {
                "coin_symbol": coin_symbol.upper(),
                "total_amount": total_amount,
                "average_cost": average_cost,
                "current_price": current_price,
                "total_value": total_value,
                "unrealized_gain": unrealized_gain,
                "unrealized_gain_percent": unrealized_gain_percent,
                "transactions_count": len(coin_transactions),
            }
        except Exception as e:
            return {
                "coin_symbol": coin_symbol.upper(),
                "total_amount": Decimal("0"),
                "average_cost": Decimal("0"),
                "current_price": Decimal("0"),
                "total_value": Decimal("0"),
                "unrealized_gain": Decimal("0"),
                "unrealized_gain_percent": Decimal("0"),
                "transactions_count": 0,
            }
    
    async def get_coin_transactions(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        wallet_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get transaction history for a specific coin."""
        try:
            # Get all transactions (with higher limit to filter by coin)
            transactions = self.db_service.get_user_transactions(db, user_id, wallet_id, limit=1000)
            coin_transactions = [
                t for t in transactions
                if t.coin_symbol.upper() == coin_symbol.upper()
            ]
            
            # Sort by date descending
            coin_transactions.sort(key=lambda x: x.transaction_date, reverse=True)
            
            # Apply pagination
            paginated = coin_transactions[offset:offset + limit]
            
            return [
                {
                    "id": str(t.id),
                    "coin_symbol": t.coin_symbol,
                    "transaction_type": t.transaction_type,
                    "amount": t.amount,
                    "price": t.price,
                    "fee": t.fee or Decimal("0"),
                    "notes": t.notes,
                    "transaction_date": t.transaction_date.isoformat(),
                }
                for t in paginated
            ]
        except Exception as e:
            return []
    
    async def get_coin_dca_plans(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        wallet_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Get DCA plans for a specific coin."""
        try:
            dca_plans = self.db_service.get_dca_plans(db, user_id, wallet_id)
            coin_plans = [
                plan for plan in dca_plans
                if plan.coin_symbol.upper() == coin_symbol.upper()
            ]
            
            return [
                {
                    "id": str(plan.id),
                    "coin_symbol": plan.coin_symbol,
                    "amount": plan.amount_per_period,  # Fixed: use amount_per_period
                    "frequency": plan.period_type,  # Fixed: use period_type
                    "start_date": plan.start_date.isoformat(),
                    "end_date": plan.end_date.isoformat() if plan.end_date else None,
                    "is_active": plan.is_active,
                    "next_execution_date": None,  # Not in model, calculate if needed
                    "total_executions": 0,  # Not in model, calculate from executions if needed
                    "total_invested": 0,  # Not in model, calculate from executions if needed
                }
                for plan in coin_plans
            ]
        except Exception as e:
            return []
    
    # Bind methods to service class
    service_class.get_coin_position = get_coin_position
    service_class.get_coin_transactions = get_coin_transactions
    service_class.get_coin_dca_plans = get_coin_dca_plans
    
    return service_class

