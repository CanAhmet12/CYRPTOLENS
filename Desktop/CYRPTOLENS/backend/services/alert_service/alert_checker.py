"""
Alert Checker Service
Checks and triggers price alerts.
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from uuid import UUID
from decimal import Decimal
import logging
from .database_service import AlertDatabaseService


class AlertChecker:
    """Service for checking and triggering alerts."""
    
    def __init__(self, notification_service=None):
        self.db_service = AlertDatabaseService()
        self.notification_service = notification_service
    
    def check_price_alerts(
        self, db: Session, user_id: UUID, coin_symbol: str, current_price: float
    ) -> List[Dict]:
        """
        Check price alerts for a coin and trigger if conditions are met.
        
        Returns list of triggered alerts.
        """
        triggered_alerts = []
        
        try:
            # Get active price alerts for this coin
            all_alerts = self.db_service.get_user_alerts(db, user_id)
            price_alerts = [
                alert for alert in all_alerts
                if alert.enabled
                and not alert.triggered
                and alert.alert_type == "price"
                and alert.coin_symbol.upper() == coin_symbol.upper()
            ]
            
            for alert in price_alerts:
                should_trigger = False
                alert_value = float(alert.value)
                
                if alert.condition == "above" and current_price >= alert_value:
                    should_trigger = True
                elif alert.condition == "below" and current_price <= alert_value:
                    should_trigger = True
                elif alert.condition == "change_percent":
                    # This would require previous price, handled separately
                    pass
                
                if should_trigger:
                    # Mark alert as triggered
                    self.db_service.mark_alert_triggered(db, alert.id)
                    
                    # Send push notification
                    if self.notification_service:
                        try:
                            self.notification_service.send_alert_notification(
                                db=db,
                                user_id=user_id,
                                coin_symbol=coin_symbol,
                                alert_type=alert.alert_type,
                                condition=alert.condition,
                                value=alert_value,
                                current_value=current_price,
                            )
                        except Exception as e:
                            logging.error(f"Failed to send notification for alert {alert.id}: {e}")
                    
                    triggered_alerts.append({
                        "alert_id": str(alert.id),
                        "coin_symbol": coin_symbol,
                        "condition": alert.condition,
                        "threshold": alert_value,
                        "current_value": current_price,
                    })
            
            return triggered_alerts
            
        except Exception as e:
            logging.error(f"Error checking price alerts: {e}")
            return []

