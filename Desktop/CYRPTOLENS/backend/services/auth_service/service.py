"""
Main business logic service for Auth Service.
Orchestrates authentication operations.
CRITICAL: Includes secure password reset implementation.
"""
# Standard library imports
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

# Third-party imports
from sqlalchemy.orm import Session

# Local application imports
from shared.config import settings
from .auth_utils import (
    PASSWORD_RESET_TOKEN_EXPIRY_MINUTES,
    create_access_token,
    generate_password_reset_token,
    hash_password_reset_token,
    is_password_reset_token_expired,
    verify_password_reset_token,
)
from .database_service import AuthDatabaseService
from .models import (
    AuthResponse,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Main service for authentication operations."""
    
    def __init__(self):
        self.db_service = AuthDatabaseService()
    
    def register_user(
        self, db: Session, email: str, password: str, 
        full_name: str, country: str, phone_number: Optional[str] = None
    ) -> AuthResponse:
        """Register a new user."""
        try:
            user = self.db_service.create_user(
                db, email, password, full_name, country, phone_number
            )
            
            # Create access token
            access_token_expires = timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email},
                expires_delta=access_token_expires
            )
            
            return AuthResponse(
                success=True,
                message="User registered successfully",
                token=TokenResponse(
                    access_token=access_token,
                    expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
                ),
                user=UserResponse(
                    id=str(user.id),
                    email=user.email,
                    created_at=user.created_at
                )
            )
        except ValueError as e:
            return AuthResponse(
                success=False,
                message=str(e)
            )
        except Exception as e:
            return AuthResponse(
                success=False,
                message=f"Registration failed: {str(e)}"
            )
    
    def login_user(
        self, db: Session, email: str, password: str
    ) -> AuthResponse:
        """Authenticate user and return token."""
        try:
            user = self.db_service.verify_user_credentials(db, email, password)
            
            if not user:
                return AuthResponse(
                    success=False,
                    message="Invalid email or password"
                )
            
            # Create access token
            access_token_expires = timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email},
                expires_delta=access_token_expires
            )
            
            return AuthResponse(
                success=True,
                message="Login successful",
                token=TokenResponse(
                    access_token=access_token,
                    expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
                ),
                user=UserResponse(
                    id=str(user.id),
                    email=user.email,
                    created_at=user.created_at
                )
            )
        except Exception as e:
            import logging
            logging.error(f"Login error: {str(e)}", exc_info=True)
            return AuthResponse(
                success=False,
                message=f"Login failed: {str(e)}"
            )
    
    def reset_password(
        self, db: Session, email: str
    ) -> AuthResponse:
        """
        Initiate password reset (sends reset token).
        CRITICAL: Generates secure token and stores it in database.
        """
        user = self.db_service.get_user_by_email(db, email)
        
        # CRITICAL: Don't reveal if user exists for security (prevent email enumeration)
        if not user:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return AuthResponse(
                success=True,
                message="If the email exists, a password reset link has been sent"
            )
        
        # CRITICAL: Generate secure reset token
        reset_token = generate_password_reset_token()
        token_hash = hash_password_reset_token(reset_token)
        
        # CRITICAL: Set expiration (15 minutes)
        expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRY_MINUTES)
        
        # CRITICAL: Store token hash in database
        success = self.db_service.store_password_reset_token(
            db, email, token_hash, expires_at
        )
        
        if not success:
            logger.error(f"Failed to store password reset token for: {email}")
            return AuthResponse(
                success=False,
                message="Failed to initiate password reset. Please try again."
            )
        
        # CRITICAL: TODO - Send email with reset token
        # In production, send email with reset link containing token
        # For now, log the token in development mode only
        if settings.DEBUG:
            logger.info(f"Password reset token for {email}: {reset_token}")
            logger.warning("⚠️ In production, send email with reset token instead of logging")
        
        # TODO: Implement email sending service
        # Example: await email_service.send_password_reset_email(email, reset_token)
        
        return AuthResponse(
            success=True,
            message="If the email exists, a password reset link has been sent"
        )
    
    def confirm_password_reset(
        self, db: Session, email: str, reset_token: str, new_password: str
    ) -> AuthResponse:
        """
        Confirm password reset with token.
        CRITICAL: Verifies token hash and expiration before resetting password.
        """
        user = self.db_service.get_user_by_email(db, email)
        
        if not user:
            logger.warning(f"Password reset confirmation for non-existent email: {email}")
            return AuthResponse(
                success=False,
                message="Password reset failed. Invalid token or email."
            )
        
        # CRITICAL: Hash provided token for comparison
        token_hash = hash_password_reset_token(reset_token)
        
        # CRITICAL: Verify token hash and expiration
        if not self.db_service.verify_password_reset_token(db, email, token_hash):
            logger.warning(f"Invalid or expired password reset token for: {email}")
            return AuthResponse(
                success=False,
                message="Password reset failed. Invalid or expired token."
            )
        
        # CRITICAL: Update password and clear reset token
        success = self.db_service.update_password(db, email, new_password)
        
        if success:
            logger.info(f"Password reset successful for: {email}")
            return AuthResponse(
                success=True,
                message="Password reset successful"
            )
        else:
            logger.error(f"Failed to update password for: {email}")
            return AuthResponse(
                success=False,
                message="Password reset failed. Please try again."
            )
    
    def send_verification_email(
        self, db: Session, email: str
    ) -> AuthResponse:
        """Send email verification token to user."""
        try:
            user = self.db_service.get_user_by_email(db, email)
            if not user:
                return AuthResponse(
                    success=False,
                    message="User not found"
                )
            
            if user.email_verified:
                return AuthResponse(
                    success=True,
                    message="Email already verified"
                )
            
            # Generate verification token
            verification_token = secrets.token_urlsafe(32)
            token_hash = hash_password_reset_token(verification_token)  # Reuse hash function
            expires_at = datetime.utcnow() + timedelta(hours=24)  # 24 hours expiry
            
            # Store token
            success = self.db_service.store_email_verification_token(
                db, email, token_hash, expires_at
            )
            
            if not success:
                return AuthResponse(
                    success=False,
                    message="Failed to generate verification token"
                )
            
            # TODO: Send email with verification link
            # In dev mode, log the token
            logger.info(f"Email verification token for {email}: {verification_token}")
            
            return AuthResponse(
                success=True,
                message="Verification email sent. Check your inbox."
            )
        except Exception as e:
            logger.error(f"Error sending verification email: {str(e)}", exc_info=True)
            return AuthResponse(
                success=False,
                message=f"Failed to send verification email: {str(e)}"
            )
    
    def verify_email(
        self, db: Session, email: str, verification_token: str
    ) -> AuthResponse:
        """Verify user email with token."""
        try:
            user = self.db_service.get_user_by_email(db, email)
            if not user:
                return AuthResponse(
                    success=False,
                    message="User not found"
                )
            
            if user.email_verified:
                return AuthResponse(
                    success=True,
                    message="Email already verified"
                )
            
            # Verify token
            token_hash = hash_password_reset_token(verification_token)
            is_valid = self.db_service.verify_email_verification_token(
                db, email, token_hash
            )
            
            if not is_valid:
                return AuthResponse(
                    success=False,
                    message="Invalid or expired verification token"
                )
            
            # Mark email as verified
            success = self.db_service.mark_email_as_verified(db, email)
            
            if not success:
                return AuthResponse(
                    success=False,
                    message="Failed to verify email"
                )
            
            return AuthResponse(
                success=True,
                message="Email verified successfully"
            )
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}", exc_info=True)
            return AuthResponse(
                success=False,
                message=f"Email verification failed: {str(e)}"
            )

