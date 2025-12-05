"""
Notification Service main application.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID
from shared.config import settings
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from shared.database import get_db
from shared.auth_dependency import get_current_user_id
from .service import NotificationService
from .models import (
    RegisterTokenRequest,
    RegisterTokenResponse,
    NotificationHistoryResponse,
)

app = FastAPI(
    title="CryptoLens Notification Service",
    version=settings.APP_VERSION,
    description="Notification service for CryptoLens - Push notifications via FCM"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
notification_service = NotificationService()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "notification_service",
        "fcm_available": notification_service.fcm_service.is_available()
    }


@app.post("/notifications/register-token", response_model=RegisterTokenResponse)
async def register_token(
    request: RegisterTokenRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Register FCM token for push notifications."""
    return notification_service.register_token(
        db=db,
        user_id=user_id,
        fcm_token=request.fcm_token,
        device_type=request.device_type,
    )


@app.get("/notifications/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get notification history for the current user."""
    return notification_service.get_notification_history(db, user_id, limit)

