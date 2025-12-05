"""
Alert Service main application.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID
from shared.config import settings
from shared.database import get_db
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from shared.auth_dependency import get_current_user_id
from .service import AlertService
from .models import AlertRequest, AlertResponse, AlertListResponse, AlertUpdateRequest

app = FastAPI(
    title="CryptoLens Alert Service",
    version=settings.APP_VERSION,
    description="Alert service for CryptoLens - Price alerts, portfolio alerts, market alerts"
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
alert_service = AlertService()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "alert_service"}


@app.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get all alerts for the current user."""
    return alert_service.get_user_alerts(db, user_id)


@app.post("/alerts", response_model=AlertResponse)
async def create_alert(
    request: AlertRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new alert."""
    return alert_service.create_alert(db, user_id, request)


@app.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: UUID,
    request: AlertUpdateRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update an alert."""
    try:
        return alert_service.update_alert(db, alert_id, user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete an alert."""
    result = alert_service.delete_alert(db, alert_id, user_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.get("/alerts/history", response_model=AlertListResponse)
async def get_alert_history(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get alert history (triggered alerts) for the current user."""
    return alert_service.get_alert_history(db, user_id)


# Coin-Specific Alert Endpoints

@app.get("/coins/{coin_symbol}/alerts", response_model=AlertListResponse)
async def get_coin_alerts(
    coin_symbol: str,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get all alerts for a specific coin."""
    return alert_service.get_coin_alerts(db, user_id, coin_symbol)


@app.post("/coins/{coin_symbol}/alerts", response_model=AlertResponse)
async def create_coin_alert(
    coin_symbol: str,
    request: AlertRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new alert for a specific coin."""
    # Ensure coin_symbol matches
    if request.coin_symbol and request.coin_symbol.upper() != coin_symbol.upper():
        raise HTTPException(
            status_code=400,
            detail="Coin symbol mismatch"
        )
    # Override coin_symbol from path
    request.coin_symbol = coin_symbol.upper()
    return alert_service.create_alert(db, user_id, request)
