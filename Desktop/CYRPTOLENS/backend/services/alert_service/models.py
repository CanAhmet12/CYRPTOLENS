"""
Alert Service Models
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from shared.validators import (
    validate_coin_symbol,
    validate_alert_type,
)


class AlertRequest(BaseModel):
    """Request model for creating an alert."""
    coin_symbol: str = Field(..., description="Coin symbol (e.g., BTC)")
    alert_type: str = Field(..., description="Alert type: price_above, price_below, change_24h, portfolio_value")
    condition: str = Field(..., description="Condition: above, below, change_percent")
    value: Decimal = Field(..., description="Threshold value")
    enabled: bool = True
    
    @field_validator('coin_symbol')
    @classmethod
    def validate_coin_symbol(cls, v: str) -> str:
        """Validate coin symbol format."""
        return validate_coin_symbol(v)
    
    @field_validator('alert_type')
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        """Validate alert type."""
        return validate_alert_type(v)


class AlertResponse(BaseModel):
    """Response model for alert."""
    id: UUID
    coin_symbol: str
    alert_type: str
    condition: str
    value: Decimal
    enabled: bool
    triggered: bool
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    """Response model for alert list."""
    alerts: list[AlertResponse]
    total: int


class AlertUpdateRequest(BaseModel):
    """Request model for updating an alert."""
    enabled: Optional[bool] = None
    value: Optional[Decimal] = None

