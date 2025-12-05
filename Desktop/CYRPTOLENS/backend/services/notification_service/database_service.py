"""
Notification Database Service
Handles database operations for notifications.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from shared.database import Base
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
import uuid


class FCMToken(Base):
    """FCM Token database model."""
    __tablename__ = "fcm_tokens"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fcm_token = Column(Text, nullable=False, unique=True)
    device_type = Column(String(20), nullable=True)  # ios, android, web
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class NotificationHistory(Base):
    """Notification history database model."""
    __tablename__ = "notification_history"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(String(20), nullable=False)  # alert, market, portfolio
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)  # Additional data (coin_symbol, etc.)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read = Column(Boolean, default=False, nullable=False)


class NotificationDatabaseService:
    """Service for notification database operations."""
    
    def register_token(self, db: Session, user_id: UUID, fcm_token: str, device_type: Optional[str] = None) -> FCMToken:
        """Register or update FCM token for a user."""
        # Check if token already exists
        existing_token = db.query(FCMToken).filter(FCMToken.fcm_token == fcm_token).first()
        
        if existing_token:
            # Update existing token
            existing_token.user_id = user_id
            existing_token.device_type = device_type
            existing_token.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_token)
            return existing_token
        else:
            # Create new token
            token = FCMToken(
                user_id=user_id,
                fcm_token=fcm_token,
                device_type=device_type,
            )
            db.add(token)
            db.commit()
            db.refresh(token)
            return token
    
    def get_user_tokens(self, db: Session, user_id: UUID) -> List[FCMToken]:
        """Get all FCM tokens for a user."""
        return db.query(FCMToken).filter(FCMToken.user_id == user_id).all()
    
    def delete_token(self, db: Session, fcm_token: str) -> bool:
        """Delete an FCM token."""
        token = db.query(FCMToken).filter(FCMToken.fcm_token == fcm_token).first()
        if not token:
            return False
        
        db.delete(token)
        db.commit()
        return True
    
    def save_notification_history(
        self, db: Session, user_id: UUID, notification_type: str,
        title: str, body: str, data: Optional[dict] = None
    ) -> NotificationHistory:
        """Save notification to history."""
        notification = NotificationHistory(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification
    
    def get_notification_history(
        self, db: Session, user_id: UUID, limit: int = 50
    ) -> List[NotificationHistory]:
        """Get notification history for a user."""
        return db.query(NotificationHistory).filter(
            NotificationHistory.user_id == user_id
        ).order_by(NotificationHistory.sent_at.desc()).limit(limit).all()
    
    def mark_notification_read(self, db: Session, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a notification as read."""
        notification = db.query(NotificationHistory).filter(
            and_(
                NotificationHistory.id == notification_id,
                NotificationHistory.user_id == user_id
            )
        ).first()
        
        if not notification:
            return False
        
        notification.read = True
        db.commit()
        return True

