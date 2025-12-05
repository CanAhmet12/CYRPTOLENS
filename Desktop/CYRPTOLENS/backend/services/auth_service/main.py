"""
Auth Service main application.
Implements all authentication endpoints as per Technical Specification.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from shared.config import settings
from shared.database import get_db
from shared.sentry_init import init_sentry

# Initialize Sentry
init_sentry()
from .service import AuthService
from .models import (
    UserRegisterRequest,
    UserLoginRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    EmailVerificationRequest,
    EmailVerificationConfirmRequest,
    AuthResponse,
)
from .auth_utils import decode_access_token

app = FastAPI(
    title="CryptoLens Auth Service",
    version=settings.APP_VERSION,
    description="Authentication service for CryptoLens - JWT authentication and user management"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Initialize service using factory (for DI support)
from shared.service_factory import get_auth_service
auth_service = get_auth_service()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """Get current user ID from JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "auth_service"}


@app.post("/auth/register", response_model=AuthResponse)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Creates a new user account and returns an access token.
    """
    return auth_service.register_user(
        db=db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        country=request.country,
        phone_number=request.phone_number
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access token.
    
    Returns JWT token for authenticated requests.
    """
    try:
        return auth_service.login_user(
            db=db,
            email=request.email,
            password=request.password
        )
    except Exception as e:
        import logging
        logging.error(f"Login endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@app.post("/auth/reset", response_model=AuthResponse)
async def reset_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset.
    
    Sends password reset email (not implemented in dev mode).
    """
    return auth_service.reset_password(
        db=db,
        email=request.email
    )


@app.post("/auth/reset/confirm", response_model=AuthResponse)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    
    Resets user password using reset token.
    """
    return auth_service.confirm_password_reset(
        db=db,
        email=request.email,
        reset_token=request.reset_token,
        new_password=request.new_password
    )


@app.post("/auth/verify/email", response_model=AuthResponse)
async def send_verification_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Send email verification token.
    
    Sends verification email to user (not implemented in dev mode).
    """
    return auth_service.send_verification_email(
        db=db,
        email=request.email
    )


@app.post("/auth/verify/email/confirm", response_model=AuthResponse)
async def confirm_email_verification(
    request: EmailVerificationConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm email verification with token.
    
    Verifies user email using verification token.
    """
    return auth_service.verify_email(
        db=db,
        email=request.email,
        verification_token=request.verification_token
    )

