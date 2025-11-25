"""
Pydantic models for Portfolio Service.
Request/Response models for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from uuid import UUID


class PortfolioItemRequest(BaseModel):
    """Request model for adding/editing portfolio item."""
    coin_symbol: str = Field(..., min_length=1, max_length=10, description="Coin symbol (e.g., BTC)")
    amount: Decimal = Field(..., gt=0, description="Amount of coins")
    buy_price: Decimal = Field(..., gt=0, description="Buy price per coin")


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

