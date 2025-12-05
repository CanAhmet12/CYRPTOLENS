"""
Shared database models for CryptoLens.
All models follow the database schema defined in Technical Specification.
"""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Integer, Text, ARRAY, Boolean, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    """Users table model."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    # CRITICAL: Password reset fields
    password_reset_token = Column(String(255), nullable=True, unique=True)
    password_reset_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Email verification fields
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(255), nullable=True, unique=True)
    email_verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Portfolio(Base):
    """Portfolio table model."""
    __tablename__ = "portfolio"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    coin_symbol = Column(String(10), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    buy_price = Column(Numeric(20, 8), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"schema": None},  # Use default schema
    )


class MarketCache(Base):
    """Market cache table model."""
    __tablename__ = "market_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    symbol = Column(String(10), unique=True, nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    volume24 = Column(Numeric(30, 2))
    dominance = Column(Numeric(5, 2))
    market_cap = Column(Numeric(30, 2))
    price_change_24h = Column(Numeric(10, 4))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Analytics(Base):
    """Analytics table model."""
    __tablename__ = "analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    coin_symbol = Column(String(10), nullable=False, unique=True)
    rsi = Column(Numeric(5, 2))
    macd = Column(Numeric(20, 8))
    macd_signal = Column(Numeric(20, 8))
    macd_histogram = Column(Numeric(20, 8))
    ema20 = Column(Numeric(20, 8))
    ema50 = Column(Numeric(20, 8))
    ema200 = Column(Numeric(20, 8))
    volatility = Column(Numeric(10, 6))
    momentum = Column(Numeric(10, 6))
    support_levels = Column(ARRAY(Numeric(20, 8)))
    resistance_levels = Column(ARRAY(Numeric(20, 8)))
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class TrendData(Base):
    """Trend data table model."""
    __tablename__ = "trend_data"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    coin_symbol = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)  # '1H', '1D', '1W', '1M', '1Y'
    trend_direction = Column(String(20))  # 'bullish', 'bearish', 'neutral'
    trend_strength = Column(Integer)  # 0-100
    trend_score = Column(Numeric(10, 4))
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class AIInsightsCache(Base):
    """AI insights cache table model (v6)."""
    __tablename__ = "ai_insights_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    insight_type = Column(String(20), nullable=False)  # 'market', 'portfolio', 'coin'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    coin_symbol = Column(String(10), nullable=True)
    insight_text = Column(Text, nullable=False)
    input_data = Column(JSONB)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))


# ============================================================
# PREMIUM PORTFOLIO FEATURES MODELS
# ============================================================

class PortfolioWallet(Base):
    """Portfolio wallets table model for multi-wallet support."""
    __tablename__ = "portfolio_wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PortfolioTransaction(Base):
    """Enhanced portfolio transactions table model."""
    __tablename__ = "portfolio_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    coin_symbol = Column(String(10), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'buy', 'sell', 'transfer', 'staking', 'airdrop', 'swap'
    amount = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0, nullable=False)
    total_cost = Column(Numeric(20, 8), nullable=False)
    notes = Column(Text, nullable=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PortfolioSnapshot(Base):
    """Portfolio snapshots table model for historical tracking."""
    __tablename__ = "portfolio_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    total_value = Column(Numeric(20, 8), nullable=False)
    total_cost = Column(Numeric(20, 8), nullable=False)
    total_profit_loss = Column(Numeric(20, 8), nullable=False)
    total_profit_loss_percent = Column(Numeric(10, 4), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PortfolioGoal(Base):
    """Portfolio goals table model."""
    __tablename__ = "portfolio_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(100), nullable=False)
    target_value = Column(Numeric(20, 8), nullable=False)
    target_date = Column(Date, nullable=True)
    current_progress = Column(Numeric(5, 2), default=0, nullable=False)  # Percentage 0-100
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PortfolioRebalancingTarget(Base):
    """Portfolio rebalancing targets table model."""
    __tablename__ = "portfolio_rebalancing_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    coin_symbol = Column(String(10), nullable=False)
    target_percentage = Column(Numeric(5, 2), nullable=False)  # 0-100
    tolerance = Column(Numeric(5, 2), default=5.0, nullable=False)  # Deviation tolerance
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PortfolioDCAPlan(Base):
    """Portfolio DCA plans table model."""
    __tablename__ = "portfolio_dca_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    coin_symbol = Column(String(10), nullable=False)
    amount_per_period = Column(Numeric(20, 8), nullable=False)
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PortfolioDCAExecution(Base):
    """Portfolio DCA executions table model."""
    __tablename__ = "portfolio_dca_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    dca_plan_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_dca_plans.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_wallets.id", ondelete="CASCADE"), nullable=True)
    coin_symbol = Column(String(10), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    total_cost = Column(Numeric(20, 8), nullable=False)
    execution_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PortfolioTaxSettings(Base):
    """Portfolio tax settings table model."""
    __tablename__ = "portfolio_tax_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    cost_basis_method = Column(String(10), default='FIFO', nullable=False)  # 'FIFO', 'LIFO', 'AVG'
    tax_year_start_month = Column(Integer, default=1, nullable=False)  # 1-12
    tax_year_start_day = Column(Integer, default=1, nullable=False)  # 1-31
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

