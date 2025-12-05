"""
Notification Service Models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class RegisterTokenRequest(BaseModel):
    """Request model for registering FCM token."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    device_type: Optional[str] = Field(None, description="Device type: ios, android, web")


class RegisterTokenResponse(BaseModel):
    """Response model for token registration."""
    success: bool
    message: str


class NotificationHistoryItem(BaseModel):
    """Model for notification history item."""
    id: UUID
    user_id: UUID
    notification_type: str  # alert, market, portfolio
    title: str
    body: str
    data: Optional[dict] = None
    sent_at: datetime
    read: bool = False


class NotificationHistoryResponse(BaseModel):
    """Response model for notification history."""
    notifications: list[NotificationHistoryItem]
    total: int

