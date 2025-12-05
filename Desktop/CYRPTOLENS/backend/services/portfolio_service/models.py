"""
Pydantic models for Portfolio Service.
Request/Response models for API endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
from shared.validators import (
    validate_coin_symbol,
    validate_transaction_type,
    validate_period_type,
    validate_export_format,
    validate_cost_basis_method,
    validate_percentage,
)


class PortfolioItemRequest(BaseModel):
    """Request model for adding/editing portfolio item."""
    coin_symbol: str = Field(..., min_length=1, max_length=10, description="Coin symbol (e.g., BTC)")
    amount: Decimal = Field(..., gt=0, description="Amount of coins")
    buy_price: Decimal = Field(..., gt=0, description="Buy price per coin")
    
    @field_validator('coin_symbol')
    @classmethod
    def validate_coin_symbol(cls, v: str) -> str:
        """Validate coin symbol format."""
        return validate_coin_symbol(v)


class PortfolioItemResponse(BaseModel):
    """Response model for portfolio item."""
    id: UUID
    coin_symbol: str
    amount: Decimal
    buy_price: Decimal
    current_price: Decimal
    total_value: Decimal
    profit_loss: Decimal
    profit_loss_percent: Decimal
    created_at: datetime
    updated_at: datetime


class PortfolioDistributionItem(BaseModel):
    """Distribution item for portfolio."""
    coin_symbol: str
    amount: Decimal
    value: Decimal
    percentage: Decimal
    profit_loss: Decimal
    profit_loss_percent: Decimal


class PortfolioResponse(BaseModel):
    """Response model for GET /portfolio."""
    total_value: Decimal
    total_profit_loss: Decimal
    total_profit_loss_percent: Decimal
    items: List[PortfolioItemResponse]
    distribution: List[PortfolioDistributionItem]
    risk_score: Optional[Decimal] = None
    volatility_score: Optional[Decimal] = None
    updated_at: datetime


class PortfolioAddResponse(BaseModel):
    """Response model for POST /portfolio/add."""
    success: bool
    message: str
    item: PortfolioItemResponse


class PortfolioEditResponse(BaseModel):
    """Response model for POST /portfolio/edit."""
    success: bool
    message: str
    item: Optional[PortfolioItemResponse] = None


class PortfolioRemoveResponse(BaseModel):
    """Response model for DELETE /portfolio/remove."""
    success: bool
    message: str


# ============================================================
# PREMIUM PORTFOLIO FEATURES MODELS
# ============================================================

# Wallet Models
class WalletRequest(BaseModel):
    """Request model for creating/updating wallet."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, description="Hex color code (e.g., #FF5733)")
    is_default: Optional[bool] = False
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None:
            return v
        from shared.validators import validate_hex_color
        return validate_hex_color(v)


class WalletResponse(BaseModel):
    """Response model for wallet."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    color: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime


# Transaction Models
class TransactionRequest(BaseModel):
    """Request model for creating transaction."""
    wallet_id: Optional[UUID] = None
    coin_symbol: str = Field(..., min_length=1, max_length=10)
    transaction_type: str = Field(..., description="Transaction type: buy, sell, transfer, staking, airdrop, swap")
    amount: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee: Decimal = Field(default=0, ge=0)
    notes: Optional[str] = None
    
    @field_validator('coin_symbol')
    @classmethod
    def validate_coin_symbol(cls, v: str) -> str:
        """Validate coin symbol format."""
        return validate_coin_symbol(v)
    
    @field_validator('transaction_type')
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        """Validate transaction type."""
        return validate_transaction_type(v)
    transaction_date: datetime


class TransactionResponse(BaseModel):
    """Response model for transaction."""
    id: UUID
    user_id: UUID
    wallet_id: Optional[UUID]
    coin_symbol: str
    transaction_type: str
    amount: Decimal
    price: Decimal
    fee: Decimal
    total_cost: Decimal
    notes: Optional[str]
    transaction_date: datetime
    created_at: datetime


# Snapshot Models
class SnapshotResponse(BaseModel):
    """Response model for portfolio snapshot."""
    id: UUID
    user_id: UUID
    wallet_id: Optional[UUID]
    total_value: Decimal
    total_cost: Decimal
    total_profit_loss: Decimal
    total_profit_loss_percent: Decimal
    snapshot_date: date
    created_at: datetime


# Goal Models
class GoalRequest(BaseModel):
    """Request model for creating/updating goal."""
    wallet_id: Optional[UUID] = None
    name: str = Field(..., min_length=1, max_length=100)
    target_value: Decimal = Field(..., gt=0)
    target_date: Optional[date] = None


class GoalResponse(BaseModel):
    """Response model for goal."""
    id: UUID
    user_id: UUID
    wallet_id: Optional[UUID]
    name: str
    target_value: Decimal
    target_date: Optional[date]
    current_progress: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Rebalancing Models
class RebalancingTargetRequest(BaseModel):
    """Request model for creating/updating rebalancing target."""
    wallet_id: Optional[UUID] = None
    coin_symbol: str = Field(..., min_length=1, max_length=10)
    target_percentage: Decimal = Field(..., ge=0, le=100)
    tolerance: Decimal = Field(default=5.0, ge=0, le=50)


class RebalancingTargetResponse(BaseModel):
    """Response model for rebalancing target."""
    id: UUID
    user_id: UUID
    wallet_id: Optional[UUID]
    coin_symbol: str
    target_percentage: Decimal
    tolerance: Decimal
    created_at: datetime
    updated_at: datetime


class RebalancingSuggestion(BaseModel):
    """Response model for rebalancing suggestion."""
    coin_symbol: str
    current_percentage: Decimal
    target_percentage: Decimal
    deviation: Decimal
    suggested_action: str  # 'buy', 'sell', 'hold'
    suggested_amount: Decimal
    suggested_value: Decimal


class RebalancingSuggestionsResponse(BaseModel):
    """Response model for rebalancing suggestions."""
    suggestions: List[RebalancingSuggestion]
    total_deviation: Decimal
    needs_rebalancing: bool


# DCA Models
class DCAPlanRequest(BaseModel):
    """Request model for creating/updating DCA plan."""
    wallet_id: Optional[UUID] = None
    coin_symbol: str = Field(..., min_length=1, max_length=10)
    amount_per_period: Decimal = Field(..., gt=0)
    period_type: str = Field(..., description="Period type: daily, weekly, monthly")
    start_date: date
    
    @field_validator('coin_symbol')
    @classmethod
    def validate_coin_symbol(cls, v: str) -> str:
        """Validate coin symbol format."""
        return validate_coin_symbol(v)
    
    @field_validator('period_type')
    @classmethod
    def validate_period_type(cls, v: str) -> str:
        """Validate period type."""
        return validate_period_type(v)
    end_date: Optional[date] = None


class DCAPlanResponse(BaseModel):
    """Response model for DCA plan."""
    id: UUID
    user_id: UUID
    wallet_id: Optional[UUID]
    coin_symbol: str
    amount_per_period: Decimal
    period_type: str
    start_date: date
    end_date: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DCAExecutionResponse(BaseModel):
    """Response model for DCA execution."""
    id: UUID
    dca_plan_id: UUID
    user_id: UUID
    wallet_id: Optional[UUID]
    coin_symbol: str
    amount: Decimal
    price: Decimal
    total_cost: Decimal
    execution_date: date
    created_at: datetime


# Tax Models
class TaxSettingsRequest(BaseModel):
    """Request model for tax settings."""
    cost_basis_method: str = Field(default='FIFO', description="Cost basis method: FIFO, LIFO, AVG")
    tax_year_start_month: int = Field(default=1, ge=1, le=12)
    tax_year_start_day: int = Field(default=1, ge=1, le=31)
    
    @field_validator('cost_basis_method')
    @classmethod
    def validate_cost_basis_method(cls, v: str) -> str:
        """Validate cost basis method."""
        return validate_cost_basis_method(v)


class TaxSettingsResponse(BaseModel):
    """Response model for tax settings."""
    id: UUID
    user_id: UUID
    cost_basis_method: str
    tax_year_start_month: int
    tax_year_start_day: int
    created_at: datetime
    updated_at: datetime


class RealizedUnrealizedResponse(BaseModel):
    """Response model for realized/unrealized gains."""
    realized_gains: Decimal
    realized_losses: Decimal
    net_realized: Decimal
    unrealized_gains: Decimal
    unrealized_losses: Decimal
    net_unrealized: Decimal
    total_gains: Decimal
    total_losses: Decimal
    net_total: Decimal


class TaxYearSummaryResponse(BaseModel):
    """Response model for tax year summary."""
    year: int
    realized_gains: Decimal
    realized_losses: Decimal
    net_capital_gains: Decimal
    transactions_count: int
    buy_transactions: int
    sell_transactions: int


# Analytics Models
class SharpeRatioResponse(BaseModel):
    """Response model for Sharpe Ratio."""
    sharpe_ratio: Decimal
    portfolio_return: Decimal
    risk_free_rate: Decimal
    portfolio_volatility: Decimal
    timeframe: str


class AlphaBetaResponse(BaseModel):
    """Response model for Alpha/Beta."""
    alpha: Decimal
    beta: Decimal
    benchmark: str
    timeframe: str


class CorrelationMatrixResponse(BaseModel):
    """Response model for correlation matrix."""
    correlations: Dict[str, Dict[str, Decimal]]
    coins: List[str]


class DrawdownResponse(BaseModel):
    """Response model for drawdown analysis."""
    max_drawdown: Decimal
    max_drawdown_percent: Decimal
    current_drawdown: Decimal
    current_drawdown_percent: Decimal
    drawdown_duration_days: int
    recovery_date: Optional[date]


class WinRateResponse(BaseModel):
    """Response model for win rate."""
    win_rate: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    break_even_trades: int


class PerformanceAttributionResponse(BaseModel):
    """Response model for performance attribution."""
    coin_symbol: str
    contribution: Decimal
    contribution_percent: Decimal
    return_percent: Decimal


class SectorAllocationResponse(BaseModel):
    """Response model for sector allocation."""
    sector: str
    value: Decimal
    percentage: Decimal
    coins: List[str]


# Benchmark Models
class BenchmarkComparisonResponse(BaseModel):
    """Response model for benchmark comparison."""
    portfolio_return: Decimal
    benchmark_return: Decimal
    outperformance: Decimal
    benchmark_name: str
    timeframe: str
    comparison_data: List[Dict[str, Any]]  # Date, portfolio_value, benchmark_value


# Export Models
class ExportRequest(BaseModel):
    """Request model for export."""
    format: str = Field(..., description="Export format: pdf, csv, excel")
    period: Optional[str] = Field(None, pattern=r'^(1M|3M|6M|1Y|ALL)$')
    year: Optional[int] = None
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate export format."""
        return validate_export_format(v)
    include_transactions: bool = True
    include_analytics: bool = True
