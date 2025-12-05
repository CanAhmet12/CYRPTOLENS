"""
Alert Service
Main business logic for alerts.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import logging
from .database_service import AlertDatabaseService
from .models import AlertRequest, AlertResponse, AlertListResponse, AlertUpdateRequest

# Try to import notification service
try:
    import sys
    import os
    # Add parent directory to path to import notification service
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from notification_service.service import NotificationService
    NOTIFICATION_SERVICE_AVAILABLE = True
except ImportError:
    NOTIFICATION_SERVICE_AVAILABLE = False
    NotificationService = None


class AlertService:
    """Main service for alert operations."""
    
    def __init__(self):
        self.db_service = AlertDatabaseService()
        # Initialize notification service if available
        self.notification_service = None
        if NOTIFICATION_SERVICE_AVAILABLE and NotificationService:
            try:
                self.notification_service = NotificationService()
            except Exception as e:
                logging.warning(f"Failed to initialize notification service: {e}")
    
    def get_user_alerts(self, db: Session, user_id: UUID) -> AlertListResponse:
        """Get all alerts for a user."""
        alerts = self.db_service.get_user_alerts(db, user_id, enabled=None, triggered=None)
        return AlertListResponse(
            alerts=[
                AlertResponse(
                    id=alert.id,
                    coin_symbol=alert.coin_symbol,
                    alert_type=alert.alert_type,
                    condition=alert.condition,
                    value=Decimal(str(alert.value)),
                    enabled=alert.enabled,
                    triggered=alert.triggered,
                    created_at=alert.created_at,
                    updated_at=alert.updated_at,
                )
                for alert in alerts
            ],
            total=len(alerts),
        )
    
    def create_alert(self, db: Session, user_id: UUID, request: AlertRequest) -> AlertResponse:
        """Create a new alert."""
        alert = self.db_service.create_alert(
            db=db,
            user_id=user_id,
            coin_symbol=request.coin_symbol,
            alert_type=request.alert_type,
            condition=request.condition,
            value=float(request.value),
            enabled=request.enabled,
        )
        return AlertResponse(
            id=alert.id,
            coin_symbol=alert.coin_symbol,
            alert_type=alert.alert_type,
            condition=alert.condition,
            value=Decimal(str(alert.value)),
            enabled=alert.enabled,
            triggered=alert.triggered,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )
    
    def update_alert(self, db: Session, alert_id: UUID, user_id: UUID, 
                    request: AlertUpdateRequest) -> AlertResponse:
        """Update an alert."""
        alert = self.db_service.update_alert(
            db=db,
            alert_id=alert_id,
            user_id=user_id,
            enabled=request.enabled,
            value=float(request.value) if request.value else None,
        )
        if not alert:
            raise ValueError("Alert not found")
        
        return AlertResponse(
            id=alert.id,
            coin_symbol=alert.coin_symbol,
            alert_type=alert.alert_type,
            condition=alert.condition,
            value=Decimal(str(alert.value)),
            enabled=alert.enabled,
            triggered=alert.triggered,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )
    
    def delete_alert(self, db: Session, alert_id: UUID, user_id: UUID) -> dict:
        """Delete an alert."""
        success = self.db_service.delete_alert(db, alert_id, user_id)
        return {"success": success, "message": "Alert deleted" if success else "Alert not found"}
    
    def get_alert_history(self, db: Session, user_id: UUID) -> AlertListResponse:
        """
        Get triggered alerts (alert history).
        ORTA: Optimized - uses database filter instead of Python filtering
        """
        # ORTA: Use database filter instead of fetching all and filtering in Python
        triggered_alerts = self.db_service.get_user_alerts(db, user_id, enabled=None, triggered=True)
        
        return AlertListResponse(
            alerts=[
                AlertResponse(
                    id=alert.id,
                    coin_symbol=alert.coin_symbol,
                    alert_type=alert.alert_type,
                    condition=alert.condition,
                    value=Decimal(str(alert.value)),
                    enabled=alert.enabled,
                    triggered=alert.triggered,
                    created_at=alert.created_at,
                    updated_at=alert.updated_at,
                )
                for alert in triggered_alerts
            ],
            total=len(triggered_alerts),
        )
    
    def get_coin_alerts(self, db: Session, user_id: UUID, coin_symbol: str) -> AlertListResponse:
        """
        Get all alerts for a specific coin.
        ORTA: Optimized - uses database filter instead of Python filtering
        """
        # ORTA: Use database filter instead of fetching all and filtering in Python
        coin_alerts = self.db_service.get_coin_alerts(db, user_id, coin_symbol)
        
        return AlertListResponse(
            alerts=[
                AlertResponse(
                    id=alert.id,
                    coin_symbol=alert.coin_symbol,
                    alert_type=alert.alert_type,
                    condition=alert.condition,
                    value=Decimal(str(alert.value)),
                    enabled=alert.enabled,
                    triggered=alert.triggered,
                    created_at=alert.created_at,
                    updated_at=alert.updated_at,
                )
                for alert in coin_alerts
            ],
            total=len(coin_alerts),
        )

