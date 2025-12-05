"""
Sentry initialization for all services.
"""
import logging
import os
from shared.config import settings

logger = logging.getLogger(__name__)

def init_sentry():
    """Initialize Sentry if DSN is provided."""
    if not settings.SENTRY_DSN:
        logger.info("ℹ️ Sentry DSN not provided. Error tracking disabled.")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        # Configure logging integration
        logging_integration = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR   # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                HttpxIntegration(),
                logging_integration,
            ],
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=1.0,
            # Release version
            release=settings.APP_VERSION,
            # Additional options
            send_default_pii=False,  # Don't send PII by default
            max_breadcrumbs=50,
        )
        logger.info("✅ Sentry initialized")
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed. Error tracking disabled.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")

