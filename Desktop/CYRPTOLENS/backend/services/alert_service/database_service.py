"""
Alert Database Service
Handles database operations for alerts.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from shared.database import Base
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
import uuid


class Alert(Base):
    """Alert database model."""
    __tablename__ = "alerts"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coin_symbol = Column(String(10), nullable=False)
    alert_type = Column(String(20), nullable=False)  # price, portfolio, market
    condition = Column(String(20), nullable=False)  # above, below, change_percent
    value = Column(Numeric(20, 8), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    triggered = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AlertDatabaseService:
    """Service for alert database operations."""
    
    def get_user_alerts(
        self, db: Session, user_id: UUID, enabled: Optional[bool] = None, triggered: Optional[bool] = None
    ) -> List[Alert]:
        """
        Get all alerts for a user.
        ORTA: Optimized query with optional filters (uses idx_alerts_user_id or idx_alerts_user_enabled)
        """
        query = db.query(Alert).filter(Alert.user_id == user_id)
        if enabled is not None:
            # ORTA: Uses composite index idx_alerts_user_enabled for filtered queries
            query = query.filter(Alert.enabled == enabled)
        if triggered is not None:
            query = query.filter(Alert.triggered == triggered)
        # ORTA: Order by created_at for consistent results
        query = query.order_by(Alert.created_at.desc())
        return query.all()
    
    def get_coin_alerts(self, db: Session, user_id: UUID, coin_symbol: str) -> List[Alert]:
        """Get all alerts for a specific coin."""
        return db.query(Alert).filter(
            and_(
                Alert.user_id == user_id,
                Alert.coin_symbol == coin_symbol.upper()
            )
        ).all()
    
    def get_alert_by_id(self, db: Session, alert_id: UUID, user_id: UUID) -> Optional[Alert]:
        """Get alert by ID."""
        return db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.user_id == user_id)
        ).first()
    
    def create_alert(self, db: Session, user_id: UUID, coin_symbol: str, alert_type: str, 
                     condition: str, value: float, enabled: bool = True) -> Alert:
        """Create a new alert."""
        alert = Alert(
            user_id=user_id,
            coin_symbol=coin_symbol.upper(),
            alert_type=alert_type,
            condition=condition,
            value=value,
            enabled=enabled,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    
    def update_alert(self, db: Session, alert_id: UUID, user_id: UUID, 
                    enabled: Optional[bool] = None, value: Optional[float] = None) -> Optional[Alert]:
        """Update an alert."""
        alert = self.get_alert_by_id(db, alert_id, user_id)
        if not alert:
            return None
        
        if enabled is not None:
            alert.enabled = enabled
        if value is not None:
            alert.value = value
        
        alert.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        return alert
    
    def delete_alert(self, db: Session, alert_id: UUID, user_id: UUID) -> bool:
        """Delete an alert."""
        alert = self.get_alert_by_id(db, alert_id, user_id)
        if not alert:
            return False
        
        db.delete(alert)
        db.commit()
        return True
    
    def get_active_alerts(self, db: Session, user_id: UUID) -> List[Alert]:
        """
        Get all active (enabled and not triggered) alerts for a user.
        ORTA: Optimized - uses get_user_alerts with filters
        """
        return self.get_user_alerts(db, user_id, enabled=True, triggered=False)
    
    def mark_alert_triggered(self, db: Session, alert_id: UUID) -> bool:
        """Mark an alert as triggered."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False
        
        alert.triggered = True
        alert.updated_at = datetime.utcnow()
        db.commit()
        return True

