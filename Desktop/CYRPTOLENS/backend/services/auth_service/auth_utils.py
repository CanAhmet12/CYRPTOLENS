"""
Authentication utilities.
JWT token generation and password hashing.
CRITICAL: Includes password reset token generation and validation.
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from shared.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CRITICAL: Password reset token expiration (15 minutes)
PASSWORD_RESET_TOKEN_EXPIRY_MINUTES = 15


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_password_reset_token() -> str:
    """
    Generate a secure password reset token.
    CRITICAL: Uses cryptographically secure random token.
    Returns a URL-safe token that can be used in password reset links.
    """
    # Generate 32-byte random token
    token_bytes = secrets.token_bytes(32)
    # Convert to URL-safe base64 string
    token = secrets.token_urlsafe(32)
    return token


def hash_password_reset_token(token: str) -> str:
    """
    Hash a password reset token for storage.
    CRITICAL: Tokens are hashed before storing in database for security.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_password_reset_token(stored_hash: str, provided_token: str) -> bool:
    """
    Verify a password reset token against stored hash.
    CRITICAL: Constant-time comparison to prevent timing attacks.
    """
    provided_hash = hashlib.sha256(provided_token.encode()).hexdigest()
    return secrets.compare_digest(stored_hash, provided_hash)


def is_password_reset_token_expired(expires_at: Optional[datetime]) -> bool:
    """
    Check if password reset token has expired.
    CRITICAL: Tokens expire after 15 minutes for security.
    """
    if expires_at is None:
        return True
    return datetime.utcnow() > expires_at


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None

