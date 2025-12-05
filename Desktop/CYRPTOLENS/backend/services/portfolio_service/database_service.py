"""
Database service for Portfolio Service.
Handles portfolio table operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, and_, or_
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from datetime import date, datetime
from shared.models import (
    Portfolio, MarketCache, PortfolioWallet, PortfolioTransaction,
    PortfolioSnapshot, PortfolioGoal, PortfolioRebalancingTarget,
    PortfolioDCAPlan, PortfolioDCAExecution, PortfolioTaxSettings
)


class PortfolioDatabaseService:
    """Service for database operations on portfolio table."""
    
    def get_user_portfolio(self, db: Session, user_id: UUID, wallet_id: Optional[UUID] = None) -> List[Portfolio]:
        """Get all portfolio items for a user."""
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        if wallet_id:
            # Filter by wallet if provided (assuming portfolio items have wallet_id)
            # Note: This requires wallet_id column in Portfolio table
            # For now, return all items if wallet_id is provided
            pass
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def get_portfolio_item(
        self, db: Session, user_id: UUID, item_id: UUID
    ) -> Optional[Portfolio]:
        """Get a specific portfolio item."""
        stmt = select(Portfolio).where(
            Portfolio.id == item_id,
            Portfolio.user_id == user_id
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_portfolio_item_by_symbol(
        self, db: Session, user_id: UUID, coin_symbol: str
    ) -> Optional[Portfolio]:
        """Get portfolio item by coin symbol."""
        stmt = select(Portfolio).where(
            Portfolio.user_id == user_id,
            Portfolio.coin_symbol == coin_symbol.upper()
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def add_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        amount: Decimal,
        buy_price: Decimal
    ) -> Portfolio:
        """Add a new portfolio item."""
        # Check if item already exists for this user and coin
        existing = self.get_portfolio_item_by_symbol(db, user_id, coin_symbol)
        if existing:
            # Update existing item
            existing.amount = amount
            existing.buy_price = buy_price
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new item
        new_item = Portfolio(
            user_id=user_id,
            coin_symbol=coin_symbol.upper(),
            amount=amount,
            buy_price=buy_price
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item
    
    def update_portfolio_item(
        self,
        db: Session,
        user_id: UUID,
        item_id: UUID,
        amount: Optional[Decimal] = None,
        buy_price: Optional[Decimal] = None
    ) -> Optional[Portfolio]:
        """Update a portfolio item."""
        item = self.get_portfolio_item(db, user_id, item_id)
        if not item:
            return None
        
        if amount is not None:
            item.amount = amount
        if buy_price is not None:
            item.buy_price = buy_price
        
        db.commit()
        db.refresh(item)
        return item
    
    def delete_portfolio_item(
        self, db: Session, user_id: UUID, item_id: UUID
    ) -> bool:
        """Delete a portfolio item."""
        item = self.get_portfolio_item(db, user_id, item_id)
        if not item:
            return False
        
        db.delete(item)
        db.commit()
        return True
    
    def get_current_price(self, db: Session, coin_symbol: str) -> Optional[Decimal]:
        """Get current price for a coin from market_cache."""
        stmt = select(MarketCache).where(
            MarketCache.symbol == coin_symbol.upper()
        )
        result = db.execute(stmt)
        market_data = result.scalar_one_or_none()
        if market_data:
            return market_data.price
        return None
    
    # ============================================================
    # PREMIUM FEATURES: WALLET METHODS
    # ============================================================
    
    def get_user_wallets(self, db: Session, user_id: UUID) -> List[PortfolioWallet]:
        """Get all wallets for a user."""
        stmt = select(PortfolioWallet).where(PortfolioWallet.user_id == user_id)
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def get_wallet(self, db: Session, user_id: UUID, wallet_id: UUID) -> Optional[PortfolioWallet]:
        """Get a specific wallet."""
        stmt = select(PortfolioWallet).where(
            PortfolioWallet.id == wallet_id,
            PortfolioWallet.user_id == user_id
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_default_wallet(self, db: Session, user_id: UUID) -> Optional[PortfolioWallet]:
        """Get user's default wallet."""
        stmt = select(PortfolioWallet).where(
            PortfolioWallet.user_id == user_id,
            PortfolioWallet.is_default == True
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def create_wallet(
        self,
        db: Session,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_default: bool = False
    ) -> PortfolioWallet:
        """Create a new wallet."""
        # If this is default, unset other defaults
        if is_default:
            stmt = select(PortfolioWallet).where(
                PortfolioWallet.user_id == user_id,
                PortfolioWallet.is_default == True
            )
            existing_defaults = db.execute(stmt).scalars().all()
            for wallet in existing_defaults:
                wallet.is_default = False
        
        new_wallet = PortfolioWallet(
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            is_default=is_default
        )
        db.add(new_wallet)
        db.commit()
        db.refresh(new_wallet)
        return new_wallet
    
    def update_wallet(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_default: Optional[bool] = None
    ) -> Optional[PortfolioWallet]:
        """Update a wallet."""
        wallet = self.get_wallet(db, user_id, wallet_id)
        if not wallet:
            return None
        
        if name is not None:
            wallet.name = name
        if description is not None:
            wallet.description = description
        if color is not None:
            wallet.color = color
        if is_default is not None:
            # If setting as default, unset other defaults
            if is_default:
                stmt = select(PortfolioWallet).where(
                    PortfolioWallet.user_id == user_id,
                    PortfolioWallet.is_default == True,
                    PortfolioWallet.id != wallet_id
                )
                existing_defaults = db.execute(stmt).scalars().all()
                for w in existing_defaults:
                    w.is_default = False
            wallet.is_default = is_default
        
        db.commit()
        db.refresh(wallet)
        return wallet
    
    def delete_wallet(self, db: Session, user_id: UUID, wallet_id: UUID) -> bool:
        """Delete a wallet."""
        wallet = self.get_wallet(db, user_id, wallet_id)
        if not wallet:
            return False
        
        db.delete(wallet)
        db.commit()
        return True
    
    # ============================================================
    # PREMIUM FEATURES: TRANSACTION METHODS
    # ============================================================
    
    def create_transaction(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID],
        coin_symbol: str,
        transaction_type: str,
        amount: Decimal,
        price: Decimal,
        fee: Decimal,
        total_cost: Decimal,
        notes: Optional[str],
        transaction_date: datetime
    ) -> PortfolioTransaction:
        """Create a new transaction."""
        new_tx = PortfolioTransaction(
            user_id=user_id,
            wallet_id=wallet_id,
            coin_symbol=coin_symbol.upper(),
            transaction_type=transaction_type,
            amount=amount,
            price=price,
            fee=fee,
            total_cost=total_cost,
            notes=notes,
            transaction_date=transaction_date
        )
        db.add(new_tx)
        db.commit()
        db.refresh(new_tx)
        return new_tx
    
    def get_user_transactions(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[PortfolioTransaction]:
        """Get transactions for a user."""
        stmt = select(PortfolioTransaction).where(
            PortfolioTransaction.user_id == user_id
        )
        if wallet_id:
            stmt = stmt.where(PortfolioTransaction.wallet_id == wallet_id)
        stmt = stmt.order_by(PortfolioTransaction.transaction_date.desc()).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    # ============================================================
    # PREMIUM FEATURES: SNAPSHOT METHODS
    # ============================================================
    
    def create_snapshot(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID],
        total_value: Decimal,
        total_cost: Decimal,
        total_profit_loss: Decimal,
        total_profit_loss_percent: Decimal,
        snapshot_date: date
    ) -> PortfolioSnapshot:
        """Create a portfolio snapshot."""
        # Check if snapshot already exists for this date
        stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.wallet_id == wallet_id,
            PortfolioSnapshot.snapshot_date == snapshot_date
        )
        existing = db.execute(stmt).scalar_one_or_none()
        
        if existing:
            # Update existing snapshot
            existing.total_value = total_value
            existing.total_cost = total_cost
            existing.total_profit_loss = total_profit_loss
            existing.total_profit_loss_percent = total_profit_loss_percent
            db.commit()
            db.refresh(existing)
            return existing
        
        new_snapshot = PortfolioSnapshot(
            user_id=user_id,
            wallet_id=wallet_id,
            total_value=total_value,
            total_cost=total_cost,
            total_profit_loss=total_profit_loss,
            total_profit_loss_percent=total_profit_loss_percent,
            snapshot_date=snapshot_date
        )
        db.add(new_snapshot)
        db.commit()
        db.refresh(new_snapshot)
        return new_snapshot
    
    def get_snapshots(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[PortfolioSnapshot]:
        """Get snapshots for a user."""
        stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id
        )
        if wallet_id:
            stmt = stmt.where(PortfolioSnapshot.wallet_id == wallet_id)
        if start_date:
            stmt = stmt.where(PortfolioSnapshot.snapshot_date >= start_date)
        if end_date:
            stmt = stmt.where(PortfolioSnapshot.snapshot_date <= end_date)
        stmt = stmt.order_by(PortfolioSnapshot.snapshot_date.asc())
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    # ============================================================
    # PREMIUM FEATURES: GOAL METHODS
    # ============================================================
    
    def get_user_goals(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> List[PortfolioGoal]:
        """Get goals for a user."""
        stmt = select(PortfolioGoal).where(PortfolioGoal.user_id == user_id)
        if wallet_id:
            stmt = stmt.where(PortfolioGoal.wallet_id == wallet_id)
        if is_active is not None:
            stmt = stmt.where(PortfolioGoal.is_active == is_active)
        stmt = stmt.order_by(PortfolioGoal.created_at.desc())
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def create_goal(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID],
        name: str,
        target_value: Decimal,
        target_date: Optional[date] = None
    ) -> PortfolioGoal:
        """Create a new goal."""
        new_goal = PortfolioGoal(
            user_id=user_id,
            wallet_id=wallet_id,
            name=name,
            target_value=target_value,
            target_date=target_date
        )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        return new_goal
    
    def update_goal(
        self,
        db: Session,
        user_id: UUID,
        goal_id: UUID,
        name: Optional[str] = None,
        target_value: Optional[Decimal] = None,
        target_date: Optional[date] = None,
        current_progress: Optional[Decimal] = None,
        is_active: Optional[bool] = None
    ) -> Optional[PortfolioGoal]:
        """Update a goal."""
        stmt = select(PortfolioGoal).where(
            PortfolioGoal.id == goal_id,
            PortfolioGoal.user_id == user_id
        )
        goal = db.execute(stmt).scalar_one_or_none()
        if not goal:
            return None
        
        if name is not None:
            goal.name = name
        if target_value is not None:
            goal.target_value = target_value
        if target_date is not None:
            goal.target_date = target_date
        if current_progress is not None:
            goal.current_progress = current_progress
        if is_active is not None:
            goal.is_active = is_active
        
        db.commit()
        db.refresh(goal)
        return goal
    
    def delete_goal(self, db: Session, user_id: UUID, goal_id: UUID) -> bool:
        """Delete a goal."""
        stmt = select(PortfolioGoal).where(
            PortfolioGoal.id == goal_id,
            PortfolioGoal.user_id == user_id
        )
        goal = db.execute(stmt).scalar_one_or_none()
        if not goal:
            return False
        
        db.delete(goal)
        db.commit()
        return True
    
    # ============================================================
    # PREMIUM FEATURES: REBALANCING METHODS
    # ============================================================
    
    def get_rebalancing_targets(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None
    ) -> List[PortfolioRebalancingTarget]:
        """Get rebalancing targets for a user."""
        stmt = select(PortfolioRebalancingTarget).where(
            PortfolioRebalancingTarget.user_id == user_id
        )
        if wallet_id:
            stmt = stmt.where(PortfolioRebalancingTarget.wallet_id == wallet_id)
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def create_rebalancing_target(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID],
        coin_symbol: str,
        target_percentage: Decimal,
        tolerance: Decimal = Decimal('5.0')
    ) -> PortfolioRebalancingTarget:
        """Create or update a rebalancing target."""
        stmt = select(PortfolioRebalancingTarget).where(
            PortfolioRebalancingTarget.user_id == user_id,
            PortfolioRebalancingTarget.wallet_id == wallet_id,
            PortfolioRebalancingTarget.coin_symbol == coin_symbol.upper()
        )
        existing = db.execute(stmt).scalar_one_or_none()
        
        if existing:
            existing.target_percentage = target_percentage
            existing.tolerance = tolerance
            db.commit()
            db.refresh(existing)
            return existing
        
        new_target = PortfolioRebalancingTarget(
            user_id=user_id,
            wallet_id=wallet_id,
            coin_symbol=coin_symbol.upper(),
            target_percentage=target_percentage,
            tolerance=tolerance
        )
        db.add(new_target)
        db.commit()
        db.refresh(new_target)
        return new_target
    
    def delete_rebalancing_target(
        self,
        db: Session,
        user_id: UUID,
        coin_symbol: str,
        wallet_id: Optional[UUID] = None
    ) -> bool:
        """Delete a rebalancing target."""
        stmt = select(PortfolioRebalancingTarget).where(
            PortfolioRebalancingTarget.user_id == user_id,
            PortfolioRebalancingTarget.coin_symbol == coin_symbol.upper()
        )
        if wallet_id:
            stmt = stmt.where(PortfolioRebalancingTarget.wallet_id == wallet_id)
        target = db.execute(stmt).scalar_one_or_none()
        if not target:
            return False
        
        db.delete(target)
        db.commit()
        return True
    
    # ============================================================
    # PREMIUM FEATURES: DCA METHODS
    # ============================================================
    
    def get_dca_plans(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> List[PortfolioDCAPlan]:
        """Get DCA plans for a user."""
        stmt = select(PortfolioDCAPlan).where(PortfolioDCAPlan.user_id == user_id)
        if wallet_id:
            stmt = stmt.where(PortfolioDCAPlan.wallet_id == wallet_id)
        if is_active is not None:
            stmt = stmt.where(PortfolioDCAPlan.is_active == is_active)
        stmt = stmt.order_by(PortfolioDCAPlan.created_at.desc())
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def create_dca_plan(
        self,
        db: Session,
        user_id: UUID,
        wallet_id: Optional[UUID],
        coin_symbol: str,
        amount_per_period: Decimal,
        period_type: str,
        start_date: date,
        end_date: Optional[date] = None
    ) -> PortfolioDCAPlan:
        """Create a new DCA plan."""
        new_plan = PortfolioDCAPlan(
            user_id=user_id,
            wallet_id=wallet_id,
            coin_symbol=coin_symbol.upper(),
            amount_per_period=amount_per_period,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return new_plan
    
    def update_dca_plan(
        self,
        db: Session,
        user_id: UUID,
        plan_id: UUID,
        amount_per_period: Optional[Decimal] = None,
        period_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_active: Optional[bool] = None
    ) -> Optional[PortfolioDCAPlan]:
        """Update a DCA plan."""
        stmt = select(PortfolioDCAPlan).where(
            PortfolioDCAPlan.id == plan_id,
            PortfolioDCAPlan.user_id == user_id
        )
        plan = db.execute(stmt).scalar_one_or_none()
        if not plan:
            return None
        
        if amount_per_period is not None:
            plan.amount_per_period = amount_per_period
        if period_type is not None:
            plan.period_type = period_type
        if start_date is not None:
            plan.start_date = start_date
        if end_date is not None:
            plan.end_date = end_date
        if is_active is not None:
            plan.is_active = is_active
        
        db.commit()
        db.refresh(plan)
        return plan
    
    def delete_dca_plan(self, db: Session, user_id: UUID, plan_id: UUID) -> bool:
        """Delete a DCA plan."""
        stmt = select(PortfolioDCAPlan).where(
            PortfolioDCAPlan.id == plan_id,
            PortfolioDCAPlan.user_id == user_id
        )
        plan = db.execute(stmt).scalar_one_or_none()
        if not plan:
            return False
        
        db.delete(plan)
        db.commit()
        return True
    
    def get_dca_executions(
        self,
        db: Session,
        user_id: UUID,
        dca_plan_id: Optional[UUID] = None,
        limit: int = 100
    ) -> List[PortfolioDCAExecution]:
        """Get DCA executions."""
        stmt = select(PortfolioDCAExecution).where(
            PortfolioDCAExecution.user_id == user_id
        )
        if dca_plan_id:
            stmt = stmt.where(PortfolioDCAExecution.dca_plan_id == dca_plan_id)
        stmt = stmt.order_by(PortfolioDCAExecution.execution_date.desc()).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())
    
    def create_dca_execution(
        self,
        db: Session,
        dca_plan_id: UUID,
        user_id: UUID,
        wallet_id: Optional[UUID],
        coin_symbol: str,
        amount: Decimal,
        price: Decimal,
        total_cost: Decimal,
        execution_date: date
    ) -> PortfolioDCAExecution:
        """Create a DCA execution record."""
        new_execution = PortfolioDCAExecution(
            dca_plan_id=dca_plan_id,
            user_id=user_id,
            wallet_id=wallet_id,
            coin_symbol=coin_symbol.upper(),
            amount=amount,
            price=price,
            total_cost=total_cost,
            execution_date=execution_date
        )
        db.add(new_execution)
        db.commit()
        db.refresh(new_execution)
        return new_execution
    
    # ============================================================
    # PREMIUM FEATURES: TAX SETTINGS METHODS
    # ============================================================
    
    def get_tax_settings(self, db: Session, user_id: UUID) -> Optional[PortfolioTaxSettings]:
        """Get tax settings for a user."""
        stmt = select(PortfolioTaxSettings).where(PortfolioTaxSettings.user_id == user_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def create_or_update_tax_settings(
        self,
        db: Session,
        user_id: UUID,
        cost_basis_method: str = 'FIFO',
        tax_year_start_month: int = 1,
        tax_year_start_day: int = 1
    ) -> PortfolioTaxSettings:
        """Create or update tax settings."""
        existing = self.get_tax_settings(db, user_id)
        
        if existing:
            existing.cost_basis_method = cost_basis_method
            existing.tax_year_start_month = tax_year_start_month
            existing.tax_year_start_day = tax_year_start_day
            db.commit()
            db.refresh(existing)
            return existing
        
        new_settings = PortfolioTaxSettings(
            user_id=user_id,
            cost_basis_method=cost_basis_method,
            tax_year_start_month=tax_year_start_month,
            tax_year_start_day=tax_year_start_day
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings

