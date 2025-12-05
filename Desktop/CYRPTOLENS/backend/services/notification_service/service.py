"""
Notification Service
Main business logic for notifications.
"""
import logging
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from .database_service import NotificationDatabaseService
from .fcm_service import FCMService
from .models import (
    RegisterTokenResponse,
    NotificationHistoryItem,
    NotificationHistoryResponse,
)

class NotificationService:
    """Main service for notification operations."""
    
    def __init__(self):
        self.db_service = NotificationDatabaseService()
        self.fcm_service = FCMService()
    
    def register_token(
        self, db: Session, user_id: UUID, fcm_token: str, device_type: Optional[str] = None
    ) -> RegisterTokenResponse:
        """Register FCM token for a user."""
        try:
            self.db_service.register_token(db, user_id, fcm_token, device_type)
            return RegisterTokenResponse(
                success=True,
                message="FCM token registered successfully"
            )
        except Exception as e:
            return RegisterTokenResponse(
                success=False,
                message=f"Failed to register token: {str(e)}"
            )
    
    def send_alert_notification(
        self, db: Session, user_id: UUID, coin_symbol: str, alert_type: str, 
        condition: str, value: float, current_value: float
    ) -> bool:
        """Send notification when an alert is triggered."""
        try:
            # Get user's FCM tokens
            tokens = self.db_service.get_user_tokens(db, user_id)
            if not tokens:
                logging.warning(f"No FCM tokens found for user {user_id}")
                return False
            
            # Prepare notification
            title = f"Alert Triggered: {coin_symbol}"
            if alert_type == "price":
                if condition == "above":
                    body = f"{coin_symbol} price is now above ${value:,.2f} (current: ${current_value:,.2f})"
                elif condition == "below":
                    body = f"{coin_symbol} price is now below ${value:,.2f} (current: ${current_value:,.2f})"
                else:
                    body = f"{coin_symbol} price alert triggered"
            else:
                body = f"Your {alert_type} alert for {coin_symbol} has been triggered"
            
            data = {
                "coin_symbol": coin_symbol,
                "alert_type": alert_type,
                "condition": condition,
                "value": str(value),
                "current_value": str(current_value),
            }
            
            # Send to all user's devices
            fcm_tokens = [token.fcm_token for token in tokens]
            result = self.fcm_service.send_multicast_notification(
                fcm_tokens=fcm_tokens,
                title=title,
                body=body,
                data=data,
                notification_type="alert"
            )
            
            # Remove invalid tokens from database
            if "invalid_tokens" in result and result["invalid_tokens"]:
                for invalid_token in result["invalid_tokens"]:
                    try:
                        self.db_service.delete_token(db, invalid_token)
                    except Exception as e:
                        logging.warning(f"Failed to delete invalid token: {e}")
            
            # Save to history
            if result["success_count"] > 0:
                self.db_service.save_notification_history(
                    db=db,
                    user_id=user_id,
                    notification_type="alert",
                    title=title,
                    body=body,
                    data=data,
                )
            
            return result["success_count"] > 0
            
        except Exception as e:
            import logging
            logging.error(f"Failed to send alert notification: {e}")
            return False
    
    def send_market_notification(
        self, db: Session, user_id: UUID, title: str, body: str, data: Optional[dict] = None
    ) -> bool:
        """Send market update notification."""
        try:
            tokens = self.db_service.get_user_tokens(db, user_id)
            if not tokens:
                return False
            
            fcm_tokens = [token.fcm_token for token in tokens]
            result = self.fcm_service.send_multicast_notification(
                fcm_tokens=fcm_tokens,
                title=title,
                body=body,
                data=data or {},
                notification_type="market"
            )
            
            # Remove invalid tokens from database
            if "invalid_tokens" in result and result["invalid_tokens"]:
                for invalid_token in result["invalid_tokens"]:
                    try:
                        self.db_service.delete_token(db, invalid_token)
                    except Exception as e:
                        logging.warning(f"Failed to delete invalid token: {e}")
            
            if result["success_count"] > 0:
                self.db_service.save_notification_history(
                    db=db,
                    user_id=user_id,
                    notification_type="market",
                    title=title,
                    body=body,
                    data=data,
                )
            
            return result["success_count"] > 0
            
        except Exception as e:
            import logging
            logging.error(f"Failed to send market notification: {e}")
            return False
    
    def send_portfolio_notification(
        self, db: Session, user_id: UUID, title: str, body: str, data: Optional[dict] = None
    ) -> bool:
        """Send portfolio update notification."""
        try:
            tokens = self.db_service.get_user_tokens(db, user_id)
            if not tokens:
                return False
            
            fcm_tokens = [token.fcm_token for token in tokens]
            result = self.fcm_service.send_multicast_notification(
                fcm_tokens=fcm_tokens,
                title=title,
                body=body,
                data=data or {},
                notification_type="portfolio"
            )
            
            # Remove invalid tokens from database
            if "invalid_tokens" in result and result["invalid_tokens"]:
                for invalid_token in result["invalid_tokens"]:
                    try:
                        self.db_service.delete_token(db, invalid_token)
                    except Exception as e:
                        logging.warning(f"Failed to delete invalid token: {e}")
            
            if result["success_count"] > 0:
                self.db_service.save_notification_history(
                    db=db,
                    user_id=user_id,
                    notification_type="portfolio",
                    title=title,
                    body=body,
                    data=data,
                )
            
            return result["success_count"] > 0
            
        except Exception as e:
            import logging
            logging.error(f"Failed to send portfolio notification: {e}")
            return False
    
    def get_notification_history(
        self, db: Session, user_id: UUID, limit: int = 50
    ) -> NotificationHistoryResponse:
        """Get notification history for a user."""
        notifications = self.db_service.get_notification_history(db, user_id, limit)
        return NotificationHistoryResponse(
            notifications=[
                NotificationHistoryItem(
                    id=notif.id,
                    user_id=notif.user_id,
                    notification_type=notif.notification_type,
                    title=notif.title,
                    body=notif.body,
                    data=notif.data,
                    sent_at=notif.sent_at,
                    read=notif.read,
                )
                for notif in notifications
            ],
            total=len(notifications),
        )

