"""
Shared configuration module for CryptoLens backend services.
All services use this configuration module.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "CryptoLens"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # JWT - CRITICAL: Must be a strong secret key (min 32 characters)
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="JWT secret key must be at least 32 characters")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @field_validator('JWT_SECRET_KEY')
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key strength."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long for security")
        if v in ['your-secret-key-change-in-production', 'test-secret-key', 'dev-secret-key']:
            raise ValueError("JWT_SECRET_KEY must not use default/example values in production")
        return v
    
    # API Keys - CRITICAL: Never hardcode API keys. Use environment variables only.
    COINGECKO_API_KEY: str = ""  # Optional: CoinGecko works without API key (free tier)
    BINANCE_API_KEY: str = ""  # Optional: Public endpoints don't require API key
    BINANCE_API_SECRET: str = ""  # Required only for authenticated endpoints
    FEAR_GREED_API_KEY: str = ""  # Optional
    
    # OpenAI (v6) - CRITICAL: Must be set via environment variable
    OPENAI_API_KEY: str = ""  # Required for AI insights feature
    OPENAI_MODEL: str = "gpt-4o"
    
    # Sentry
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # API Gateway
    API_GATEWAY_HOST: str = "0.0.0.0"
    API_GATEWAY_PORT: int = 8000
    
    # Service URLs
    AUTH_SERVICE_URL: str = "http://localhost:8001"
    MARKET_SERVICE_URL: str = "http://localhost:8002"
    PORTFOLIO_SERVICE_URL: str = "http://localhost:8003"
    ANALYTICS_SERVICE_URL: str = "http://localhost:8004"
    TREND_SERVICE_URL: str = "http://localhost:8005"
    AI_SERVICE_URL: str = "http://localhost:8006"
    WATCHLIST_SERVICE_URL: str = "http://localhost:8007"
    ALERT_SERVICE_URL: str = "http://localhost:8008"
    REALTIME_SERVICE_URL: str = "http://localhost:8009"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8010"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_production_settings(self) -> None:
        """Validate settings for production environment."""
        if self.ENVIRONMENT == "production":
            # Production-specific validations
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters in production")
            if self.JWT_SECRET_KEY == "your-secret-key-change-in-production":
                raise ValueError("JWT_SECRET_KEY must be changed from default value in production")
            if not self.DATABASE_URL or "localhost" in self.DATABASE_URL:
                raise ValueError("DATABASE_URL must not point to localhost in production")


# Global settings instance
settings = Settings()

# Validate settings on import (only in production)
if settings.ENVIRONMENT == "production":
    try:
        settings.validate_production_settings()
    except ValueError as e:
        import sys
        import logging
        logger = logging.getLogger(__name__)
        logger.critical(f"Production configuration error: {e}", exc_info=True)
        # CRITICAL: Use stderr for critical errors (allowed exception for startup)
        print(f"CRITICAL: Production configuration error: {e}", file=sys.stderr)
        sys.exit(1)

