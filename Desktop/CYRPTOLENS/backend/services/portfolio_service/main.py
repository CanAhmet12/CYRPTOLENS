"""
Portfolio Service main application.
Implements all portfolio endpoints as per Technical Specification.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from shared.config import settings
from shared.database import get_db
from .service import PortfolioService
from .models import (
    PortfolioResponse,
    PortfolioItemRequest,
    PortfolioAddResponse,
    PortfolioEditResponse,
    PortfolioRemoveResponse,
)

app = FastAPI(
    title="CryptoLens Portfolio Service",
    version=settings.APP_VERSION,
    description="Portfolio management service for CryptoLens"
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
portfolio_service = PortfolioService()


# Import authentication dependency
try:
    from shared.auth_dependency import get_current_user_id
except ImportError:
    # Fallback if auth dependency not available
    from uuid import UUID
    def get_current_user_id() -> UUID:
        """Fallback: Get current user ID from authentication token."""
        # Placeholder - replace with actual JWT authentication
        return UUID("00000000-0000-0000-0000-000000000001")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "portfolio_service"}


@app.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get user's complete portfolio.
    
    Returns:
    - Total portfolio value
    - Total profit/loss
    - List of portfolio items
    - Distribution breakdown
    - Risk and volatility scores
    """
    return await portfolio_service.get_portfolio(db, user_id)


@app.post("/portfolio/add", response_model=PortfolioAddResponse)
async def add_portfolio_item(
    item: PortfolioItemRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Add a new portfolio item.
    
    If item with same coin_symbol exists, it will be updated.
    """
    try:
        return await portfolio_service.add_portfolio_item(
            db=db,
            user_id=user_id,
            coin_symbol=item.coin_symbol,
            amount=item.amount,
            buy_price=item.buy_price
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add portfolio item: {str(e)}"
        )


@app.post("/portfolio/edit", response_model=PortfolioEditResponse)
async def edit_portfolio_item(
    item_id: UUID,
    amount: Decimal = None,
    buy_price: Decimal = None,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Edit an existing portfolio item.
    
    At least one of amount or buy_price must be provided.
    """
    if amount is None and buy_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of amount or buy_price must be provided"
        )
    
    try:
        return await portfolio_service.edit_portfolio_item(
            db=db,
            user_id=user_id,
            item_id=item_id,
            amount=amount,
            buy_price=buy_price
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to edit portfolio item: {str(e)}"
        )


@app.delete("/portfolio/remove", response_model=PortfolioRemoveResponse)
async def remove_portfolio_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Remove a portfolio item.
    """
    try:
        return portfolio_service.remove_portfolio_item(
            db=db,
            user_id=user_id,
            item_id=item_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to remove portfolio item: {str(e)}"
        )


@app.get("/portfolio/performance")
async def get_portfolio_performance(
    timeframe: str = Query(default="1D", description="Timeframe: 1D, 7D, 30D, 1Y"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get portfolio performance data for different timeframes.
    
    Returns performance data as a dictionary with timeframe keys and value arrays.
    """
    return await portfolio_service.get_portfolio_performance(db, user_id, timeframe)


@app.get("/portfolio/transactions")
async def get_transaction_history(
    limit: int = Query(default=50, ge=1, le=100, description="Number of transactions to return"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get transaction history for user's portfolio.
    
    Returns list of transactions with symbol, type, quantity, price, amount, and date.
    """
    transactions = await portfolio_service.get_transaction_history(db, user_id, limit)
    return {"transactions": transactions}
