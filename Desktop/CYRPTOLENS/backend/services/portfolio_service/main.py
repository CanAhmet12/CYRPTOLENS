"""
Portfolio Service main application.
Implements all portfolio endpoints as per Technical Specification.
"""
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from shared.config import settings
from shared.database import get_db
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from .service import PortfolioService
from .models import (
    PortfolioResponse,
    PortfolioItemRequest,
    PortfolioAddResponse,
    PortfolioEditResponse,
    PortfolioRemoveResponse,
    WalletRequest,
    WalletResponse,
    TransactionRequest,
    TransactionResponse,
    GoalRequest,
    GoalResponse,
    RebalancingTargetRequest,
    RebalancingTargetResponse,
    RebalancingSuggestionsResponse,
    DCAPlanRequest,
    DCAPlanResponse,
    TaxSettingsRequest,
    TaxSettingsResponse,
    RealizedUnrealizedResponse,
    TaxYearSummaryResponse,
    SharpeRatioResponse,
    AlphaBetaResponse,
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

# Initialize service using factory (for DI support)
from shared.service_factory import get_portfolio_service
portfolio_service = get_portfolio_service()


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


# ============================================================
# PREMIUM FEATURES ENDPOINTS
# ============================================================

# Wallet Endpoints
@app.get("/portfolio/wallets", response_model=List[WalletResponse])
async def get_wallets(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get all wallets for the user."""
    wallets = await portfolio_service.get_wallets(db, user_id)
    return wallets


@app.post("/portfolio/wallets", response_model=WalletResponse)
async def create_wallet(
    wallet: WalletRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new wallet."""
    return await portfolio_service.create_wallet(
        db, user_id, wallet.name, wallet.description, wallet.color, wallet.is_default or False
    )


# Analytics Endpoints
@app.get("/portfolio/analytics/sharpe-ratio", response_model=SharpeRatioResponse)
async def get_sharpe_ratio(
    timeframe: str = Query(default="30D", description="Timeframe: 7D, 30D, 1Y"),
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get Sharpe Ratio for portfolio."""
    result = await portfolio_service.get_sharpe_ratio(db, user_id, wallet_id, timeframe)
    return SharpeRatioResponse(**result)


@app.get("/portfolio/analytics/alpha-beta", response_model=AlphaBetaResponse)
async def get_alpha_beta(
    benchmark: str = Query(default="BTC", description="Benchmark: BTC, ETH, SP500"),
    timeframe: str = Query(default="30D", description="Timeframe: 7D, 30D, 1Y"),
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get Alpha and Beta for portfolio."""
    result = await portfolio_service.get_alpha_beta(db, user_id, wallet_id, benchmark, timeframe)
    return AlphaBetaResponse(**result)


# Tax Endpoints
@app.get("/portfolio/tax/realized-unrealized", response_model=RealizedUnrealizedResponse)
async def get_realized_unrealized(
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get realized and unrealized gains/losses."""
    result = await portfolio_service.get_realized_unrealized(db, user_id, wallet_id)
    return RealizedUnrealizedResponse(**result)


@app.get("/portfolio/tax/year-summary", response_model=TaxYearSummaryResponse)
async def get_tax_year_summary(
    year: int = Query(..., description="Tax year (e.g., 2024)"),
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get tax year summary."""
    result = await portfolio_service.get_tax_year_summary(db, user_id, year, wallet_id)
    return TaxYearSummaryResponse(**result)


# Rebalancing Endpoints
@app.get("/portfolio/rebalancing/suggestions", response_model=RebalancingSuggestionsResponse)
async def get_rebalancing_suggestions(
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get rebalancing suggestions."""
    result = await portfolio_service.get_rebalancing_suggestions(db, user_id, wallet_id)
    return RebalancingSuggestionsResponse(**result)


# Export Endpoints
@app.get("/portfolio/export/{export_format}")
async def export_portfolio(
    export_format: str,
    period: str = Query(default="ALL", regex="^(1M|3M|6M|1Y|ALL)$", description="Time period"),
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Export portfolio data."""
    from fastapi.responses import StreamingResponse
    
    if export_format not in ['pdf', 'csv', 'excel']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be one of: pdf, csv, excel"
        )
    
    export_data = await portfolio_service.export_portfolio(
        db, user_id, wallet_id, export_format, period
    )
    
    if export_format == 'pdf':
        return StreamingResponse(
            export_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=portfolio_{period}.pdf"}
        )
    elif export_format == 'csv':
        from fastapi.responses import Response
        return Response(
            content=export_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=portfolio_{period}.csv"}
        )
    elif export_format == 'excel':
        return StreamingResponse(
            export_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=portfolio_{period}.xlsx"}
        )


# Goal Endpoints
@app.get("/portfolio/goals")
async def get_goals(
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get portfolio goals."""
    goals = portfolio_service.db_service.get_user_goals(db, user_id, wallet_id, is_active)
    return [
        {
            'id': str(g.id),
            'user_id': str(g.user_id),
            'wallet_id': str(g.wallet_id) if g.wallet_id else None,
            'name': g.name,
            'target_value': float(g.target_value),
            'target_date': g.target_date.isoformat() if g.target_date else None,
            'current_progress': float(g.current_progress),
            'is_active': g.is_active,
            'created_at': g.created_at.isoformat(),
            'updated_at': g.updated_at.isoformat(),
        }
        for g in goals
    ]


@app.post("/portfolio/goals")
async def create_goal(
    goal: GoalRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new goal."""
    new_goal = portfolio_service.db_service.create_goal(
        db, user_id, goal.wallet_id, goal.name, goal.target_value, goal.target_date
    )
    return {
        'id': str(new_goal.id),
        'user_id': str(new_goal.user_id),
        'wallet_id': str(new_goal.wallet_id) if new_goal.wallet_id else None,
        'name': new_goal.name,
        'target_value': float(new_goal.target_value),
        'target_date': new_goal.target_date.isoformat() if new_goal.target_date else None,
        'current_progress': float(new_goal.current_progress),
        'is_active': new_goal.is_active,
        'created_at': new_goal.created_at.isoformat(),
        'updated_at': new_goal.updated_at.isoformat(),
    }


# Rebalancing Target Endpoints
@app.get("/portfolio/rebalancing/targets")
async def get_rebalancing_targets(
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get rebalancing targets."""
    targets = portfolio_service.db_service.get_rebalancing_targets(db, user_id, wallet_id)
    return [
        {
            'id': str(t.id),
            'user_id': str(t.user_id),
            'wallet_id': str(t.wallet_id) if t.wallet_id else None,
            'coin_symbol': t.coin_symbol,
            'target_percentage': float(t.target_percentage),
            'tolerance': float(t.tolerance),
            'created_at': t.created_at.isoformat(),
            'updated_at': t.updated_at.isoformat(),
        }
        for t in targets
    ]


@app.post("/portfolio/rebalancing/targets")
async def create_rebalancing_target(
    target: RebalancingTargetRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create or update a rebalancing target."""
    new_target = portfolio_service.db_service.create_rebalancing_target(
        db, user_id, target.wallet_id, target.coin_symbol, target.target_percentage, target.tolerance
    )
    return {
        'id': str(new_target.id),
        'user_id': str(new_target.user_id),
        'wallet_id': str(new_target.wallet_id) if new_target.wallet_id else None,
        'coin_symbol': new_target.coin_symbol,
        'target_percentage': float(new_target.target_percentage),
        'tolerance': float(new_target.tolerance),
        'created_at': new_target.created_at.isoformat(),
        'updated_at': new_target.updated_at.isoformat(),
    }


# DCA Plan Endpoints
@app.get("/portfolio/dca/plans")
async def get_dca_plans(
    wallet_id: Optional[UUID] = Query(None, description="Wallet ID (optional)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get DCA plans."""
    plans = portfolio_service.db_service.get_dca_plans(db, user_id, wallet_id, is_active)
    return [
        {
            'id': str(p.id),
            'user_id': str(p.user_id),
            'wallet_id': str(p.wallet_id) if p.wallet_id else None,
            'coin_symbol': p.coin_symbol,
            'amount_per_period': float(p.amount_per_period),
            'period_type': p.period_type,
            'start_date': p.start_date.isoformat(),
            'end_date': p.end_date.isoformat() if p.end_date else None,
            'is_active': p.is_active,
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat(),
        }
        for p in plans
    ]


@app.post("/portfolio/dca/plans")
async def create_dca_plan(
    plan: DCAPlanRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new DCA plan."""
    new_plan = portfolio_service.db_service.create_dca_plan(
        db, user_id, plan.wallet_id, plan.coin_symbol, plan.amount_per_period,
        plan.period_type, plan.start_date, plan.end_date
    )
    return {
        'id': str(new_plan.id),
        'user_id': str(new_plan.user_id),
        'wallet_id': str(new_plan.wallet_id) if new_plan.wallet_id else None,
        'coin_symbol': new_plan.coin_symbol,
        'amount_per_period': float(new_plan.amount_per_period),
        'period_type': new_plan.period_type,
        'start_date': new_plan.start_date.isoformat(),
        'end_date': new_plan.end_date.isoformat() if new_plan.end_date else None,
        'is_active': new_plan.is_active,
        'created_at': new_plan.created_at.isoformat(),
        'updated_at': new_plan.updated_at.isoformat(),
    }


# Tax Settings Endpoints
@app.get("/portfolio/tax/settings", response_model=TaxSettingsResponse)
async def get_tax_settings(
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get tax settings."""
    settings = portfolio_service.db_service.get_tax_settings(db, user_id)
    if not settings:
        # Return default settings
        return TaxSettingsResponse(
            id=UUID('00000000-0000-0000-0000-000000000000'),
            user_id=user_id,
            cost_basis_method='FIFO',
            tax_year_start_month=1,
            tax_year_start_day=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    return TaxSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        cost_basis_method=settings.cost_basis_method,
        tax_year_start_month=settings.tax_year_start_month,
        tax_year_start_day=settings.tax_year_start_day,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    )


@app.post("/portfolio/tax/settings", response_model=TaxSettingsResponse)
async def update_tax_settings(
    settings: TaxSettingsRequest,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create or update tax settings."""
    updated = portfolio_service.db_service.create_or_update_tax_settings(
        db, user_id, settings.cost_basis_method,
        settings.tax_year_start_month, settings.tax_year_start_day
    )
    return TaxSettingsResponse(
        id=updated.id,
        user_id=updated.user_id,
        cost_basis_method=updated.cost_basis_method,
        tax_year_start_month=updated.tax_year_start_month,
        tax_year_start_day=updated.tax_year_start_day,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )
