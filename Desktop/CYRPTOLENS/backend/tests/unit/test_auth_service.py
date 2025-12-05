"""
Unit tests for Auth Service.
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from services.auth_service.service import AuthService
from services.auth_service.models import UserRegisterRequest


@pytest.mark.unit
class TestAuthService:
    """Test Auth Service functionality."""
    
    def test_register_user_success(self, db_session: Session):
        """Test successful user registration."""
        service = AuthService()
        
        result = service.register_user(
            db=db_session,
            email="test@example.com",
            password="Test123!@#",
            full_name="Test User",
            country="US",
            phone_number="+1234567890"
        )
        
        assert result is not None
        assert "access_token" in result
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["full_name"] == "Test User"
    
    def test_register_user_duplicate_email(self, db_session: Session):
        """Test registration with duplicate email."""
        service = AuthService()
        
        # Register first user
        service.register_user(
            db=db_session,
            email="test@example.com",
            password="Test123!@#",
            full_name="Test User",
            country="US"
        )
        
        # Try to register again with same email
        with pytest.raises(Exception):  # Should raise an exception
            service.register_user(
                db=db_session,
                email="test@example.com",
                password="Test123!@#",
                full_name="Test User 2",
                country="US"
            )
    
    def test_login_user_success(self, db_session: Session):
        """Test successful user login."""
        service = AuthService()
        
        # Register user first
        service.register_user(
            db=db_session,
            email="test@example.com",
            password="Test123!@#",
            full_name="Test User",
            country="US"
        )
        
        # Login
        result = service.login_user(
            db=db_session,
            email="test@example.com",
            password="Test123!@#"
        )
        
        assert result is not None
        assert "access_token" in result
        assert result["user"]["email"] == "test@example.com"
    
    def test_login_user_invalid_credentials(self, db_session: Session):
        """Test login with invalid credentials."""
        service = AuthService()
        
        # Register user
        service.register_user(
            db=db_session,
            email="test@example.com",
            password="Test123!@#",
            full_name="Test User",
            country="US"
        )
        
        # Try to login with wrong password
        with pytest.raises(Exception):
            service.login_user(
                db=db_session,
                email="test@example.com",
                password="WrongPassword"
            )

