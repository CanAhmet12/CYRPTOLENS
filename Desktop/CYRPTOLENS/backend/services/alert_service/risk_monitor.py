"""
Risk Alert Monitor
Monitors portfolio risk and triggers alerts when thresholds are exceeded.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from .database_service import AlertDatabaseService, Alert
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.portfolio_service.models import PortfolioResponse
from shared.analytics.portfolio.portfolio_metrics import (
    calculate_portfolio_risk_score,
    calculate_portfolio_volatility,
    calculate_diversification_score,
    PortfolioHolding,
)


class RiskMonitor:
    """Monitors portfolio risk and triggers alerts."""
    
    def __init__(self):
        self.alert_db_service = AlertDatabaseService()
    
    def check_portfolio_risk_alerts(
        self, db: Session, user_id: UUID, portfolio: 'PortfolioResponse'
    ) -> List[dict]:
        """
        Check portfolio risk and trigger alerts if thresholds are exceeded.
        
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        # Get active risk alerts for this user
        active_alerts = self.alert_db_service.get_active_alerts(db, user_id)
        risk_alerts = [a for a in active_alerts if a.alert_type == 'portfolio']
        
        if not risk_alerts:
            return triggered_alerts
        
        # Calculate portfolio metrics
        holdings = self._convert_to_holdings(portfolio)
        
        if not holdings:
            return triggered_alerts
        
        risk_score = float(calculate_portfolio_risk_score(holdings))
        volatility = float(calculate_portfolio_volatility(holdings))
        diversification = float(calculate_diversification_score(holdings))
        concentration = 100 - diversification
        
        # Check each alert
        for alert in risk_alerts:
            should_trigger = False
            alert_value = float(alert.value)
            
            if alert.condition == 'above':
                if alert.coin_symbol == 'RISK_SCORE' and risk_score > alert_value:
                    should_trigger = True
                elif alert.coin_symbol == 'VOLATILITY' and volatility > alert_value:
                    should_trigger = True
                elif alert.coin_symbol == 'CONCENTRATION' and concentration > alert_value:
                    should_trigger = True
                elif alert.coin_symbol == 'VALUE_DROP':
                    # Value drop is handled separately
                    pass
            elif alert.condition == 'below':
                if alert.coin_symbol == 'DIVERSIFICATION' and diversification < alert_value:
                    should_trigger = True
            
            if should_trigger and not alert.triggered:
                # Mark alert as triggered
                self.alert_db_service.mark_alert_triggered(db, alert.id)
                triggered_alerts.append({
                    'alert_id': str(alert.id),
                    'type': alert.coin_symbol,
                    'condition': alert.condition,
                    'threshold': alert_value,
                    'current_value': risk_score if alert.coin_symbol == 'RISK_SCORE' 
                                      else volatility if alert.coin_symbol == 'VOLATILITY'
                                      else concentration if alert.coin_symbol == 'CONCENTRATION'
                                      else diversification,
                })
        
        return triggered_alerts
    
    def check_portfolio_value_drop(
        self, db: Session, user_id: UUID, 
        current_value: Decimal, previous_value: Optional[Decimal]
    ) -> List[dict]:
        """
        Check if portfolio value dropped significantly.
        
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        if previous_value is None or previous_value == 0:
            return triggered_alerts
        
        # Calculate drop percentage
        drop_percent = float((previous_value - current_value) / previous_value * 100)
        
        # Get active value drop alerts
        active_alerts = self.alert_db_service.get_active_alerts(db, user_id)
        value_drop_alerts = [
            a for a in active_alerts 
            if a.alert_type == 'portfolio' 
            and a.coin_symbol == 'VALUE_DROP'
            and a.condition == 'above'
        ]
        
        for alert in value_drop_alerts:
            if drop_percent >= float(alert.value) and not alert.triggered:
                self.alert_db_service.mark_alert_triggered(db, alert.id)
                triggered_alerts.append({
                    'alert_id': str(alert.id),
                    'type': 'VALUE_DROP',
                    'threshold': float(alert.value),
                    'drop_percent': drop_percent,
                    'current_value': float(current_value),
                    'previous_value': float(previous_value),
                })
        
        return triggered_alerts
    
    def _convert_to_holdings(self, portfolio: 'PortfolioResponse') -> List[PortfolioHolding]:
        """Convert portfolio response to holdings list."""
        holdings = []
        
        if not portfolio or not portfolio.items:
            return holdings
        
        for item in portfolio.items:
            holdings.append(
                PortfolioHolding(
                    symbol=item.coin_symbol,
                    amount=Decimal(str(item.amount)),
                    buy_price=Decimal(str(item.buy_price)) if item.buy_price else None,
                    current_price=Decimal(str(item.current_price)) if item.current_price else Decimal(0),
                    volatility=None,  # Will be calculated if available
                )
            )
        
        return holdings

