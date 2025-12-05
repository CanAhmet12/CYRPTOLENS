"""
Pydantic models for Auth Service.
Request/Response models for API endpoints.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from shared.validators import (
    validate_password_strength,
    validate_phone_number,
)


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Password must be at least 8 characters with uppercase, lowercase, digit, and special character"
    )
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    country: str = Field(..., min_length=2, max_length=100, description="Country name")
    phone_number: Optional[str] = Field(
        None,
        max_length=20,
        description="Phone number in E.164 format (e.g., +1234567890)"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format."""
        if v is None:
            return v
        return validate_phone_number(v)


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Request model for password reset."""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Request model for password reset confirmation."""
    email: EmailStr
    reset_token: str
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password must be at least 8 characters with uppercase, lowercase, digit, and special character"
    )
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)


class EmailVerificationRequest(BaseModel):
    """Request model for email verification."""
    email: EmailStr


class EmailVerificationConfirmRequest(BaseModel):
    """Request model for email verification confirmation."""
    email: EmailStr
    verification_token: str


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Response model for user data."""
    id: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    """Response model for authentication."""
    success: bool
    message: str
    token: Optional[TokenResponse] = None
    user: Optional[UserResponse] = None

