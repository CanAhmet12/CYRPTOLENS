"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import Base, get_db
from shared.config import settings


# Test database URL (in-memory SQLite for unit tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Create a test database session.
    Uses in-memory SQLite for fast unit tests.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session: Session):
    """Override get_db dependency for testing."""
    def _get_db():
        try:
            yield db_session
        finally:
            pass
    return _get_db


@pytest.fixture(scope="function")
def test_client(override_get_db):
    """Create a test client for FastAPI apps."""
    # This will be overridden by specific service test clients
    pass


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(base_url="http://test", timeout=30.0) as client:
        yield client


@pytest.fixture(scope="function")
def mock_redis(monkeypatch):
    """Mock Redis client for tests."""
    class MockRedis:
        def __init__(self):
            self._data = {}
        
        async def get(self, key: str):
            return self._data.get(key)
        
        async def set(self, key: str, value: str, ex: int = None):
            self._data[key] = value
            return True
        
        async def delete(self, key: str):
            return self._data.pop(key, None) is not None
        
        async def exists(self, key: str):
            return key in self._data
    
    mock_redis = MockRedis()
    # This will be used by services that need Redis
    return mock_redis


@pytest.fixture(scope="function")
def mock_httpx_client(monkeypatch):
    """Mock HTTPX client for external API calls."""
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json_data = json_data
            self.text = text
        
        def json(self):
            return self._json_data or {}
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    class MockClient:
        def __init__(self):
            self.responses = {}
        
        async def get(self, url, **kwargs):
            return self.responses.get("get", MockResponse())
        
        async def post(self, url, **kwargs):
            return self.responses.get("post", MockResponse())
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    return MockClient()


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    """Reset settings to test values before each test."""
    # Override environment variables for testing
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
    monkeypatch.setenv("SENTRY_DSN", "")  # Disable Sentry in tests

