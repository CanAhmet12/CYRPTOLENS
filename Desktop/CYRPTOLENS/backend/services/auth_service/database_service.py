"""
Database service for Auth Service.
Handles user table operations.
CRITICAL: Includes password reset token management.
"""
import secrets
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime
from shared.models import User
from .auth_utils import get_password_hash, verify_password


class AuthDatabaseService:
    """Service for database operations on users table."""
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email.lower())
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_user_by_id(self, db: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def create_user(
        self, db: Session, email: str, password: str,
        full_name: str, country: str, phone_number: Optional[str] = None
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        existing = self.get_user_by_email(db, email)
        if existing:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = get_password_hash(password)
        
        # Create user
        new_user = User(
            email=email.lower(),
            password_hash=hashed_password,
            full_name=full_name,
            country=country,
            phone_number=phone_number
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    
    def verify_user_credentials(
        self, db: Session, email: str, password: str
    ) -> Optional[User]:
        """Verify user credentials."""
        try:
            user = self.get_user_by_email(db, email)
            if not user:
                return None
            
            if not verify_password(password, user.password_hash):
                return None
            
            return user
        except Exception as e:
            import logging
            logging.error(f"Error verifying credentials: {str(e)}", exc_info=True)
            raise
    
    def update_password(
        self, db: Session, email: str, new_password: str
    ) -> bool:
        """Update user password."""
        user = self.get_user_by_email(db, email)
        if not user:
            return False
        
        hashed_password = get_password_hash(new_password)
        user.password_hash = hashed_password
        # CRITICAL: Clear password reset token after successful reset
        user.password_reset_token = None
        user.password_reset_token_expires_at = None
        db.commit()
        db.refresh(user)
        return True
    
    def store_password_reset_token(
        self, db: Session, email: str, token_hash: str, expires_at: datetime
    ) -> bool:
        """
        Store password reset token for user.
        CRITICAL: Token is hashed before storage for security.
        """
        user = self.get_user_by_email(db, email)
        if not user:
            return False
        
        user.password_reset_token = token_hash
        user.password_reset_token_expires_at = expires_at
        db.commit()
        db.refresh(user)
        return True
    
    def verify_password_reset_token(
        self, db: Session, email: str, token_hash: str
    ) -> bool:
        """
        Verify password reset token for user.
        CRITICAL: Checks token hash and expiration.
        """
        user = self.get_user_by_email(db, email)
        if not user:
            return False
        
        if not user.password_reset_token:
            return False
        
        # CRITICAL: Constant-time comparison
        if not secrets.compare_digest(user.password_reset_token, token_hash):
            return False
        
        # CRITICAL: Check expiration
        if user.password_reset_token_expires_at is None:
            return False
        
        from datetime import datetime
        if datetime.utcnow() > user.password_reset_token_expires_at:
            return False
        
        return True
    
    def store_email_verification_token(
        self, db: Session, email: str, token_hash: str, expires_at: datetime
    ) -> bool:
        """Store email verification token for user."""
        user = self.get_user_by_email(db, email)
        if not user:
            return False
        
        user.email_verification_token = token_hash
        user.email_verification_token_expires_at = expires_at
        db.commit()
        db.refresh(user)
        return True
    
    def verify_email_verification_token(
        self, db: Session, email: str, token_hash: str
    ) -> bool:
        """Verify email verification token for user."""
        user = self.get_user_by_email(db, email)
        if not user:
            return False
        
        if not user.email_verification_token:
            return False
        
        # Constant-time comparison
        if not secrets.compare_digest(user.email_verification_token, token_hash):
            return False
        
        # Check expiration
        if user.email_verification_token_expires_at is None:
            return False
        
        if datetime.utcnow() > user.email_verification_token_expires_at:
            return False
        
        return True
    
    def mark_email_as_verified(self, db: Session, email: str) -> bool:
        """Mark user email as verified."""
        user = self.get_user_by_email(db, email)
        if not user:
            return False
        
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires_at = None
        db.commit()
        db.refresh(user)
        return True

