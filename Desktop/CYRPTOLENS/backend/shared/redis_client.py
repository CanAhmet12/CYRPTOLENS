"""
Shared Redis client module for CryptoLens backend services.
Used for caching high-frequency data.
CRITICAL: Includes connection error handling and reconnection logic.
"""
import redis
import logging
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)

# Create Redis connection pool with error handling
try:
    redis_pool = redis.ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        decode_responses=True,
        max_connections=50,
        retry_on_timeout=True,
        health_check_interval=30,  # CRITICAL: Health check every 30 seconds
    )
    
    # Global Redis client with connection error handling
    redis_client = redis.Redis(
        connection_pool=redis_pool,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    
    # Test connection on initialization
    try:
        redis_client.ping()
        logger.info("✅ Redis connection established")
    except redis.ConnectionError as e:
        logger.warning(f"⚠️ Redis connection failed: {e}. Cache will be disabled.")
        redis_client = None  # CRITICAL: Set to None if connection fails
except Exception as e:
    logger.error(f"❌ Failed to initialize Redis: {e}", exc_info=True)
    redis_client = None  # CRITICAL: Set to None if initialization fails


def get_redis() -> Optional[redis.Redis]:
    """
    Get Redis client instance.
    CRITICAL: Returns None if Redis is unavailable (graceful degradation).
    
    Usage:
        redis_client = get_redis()
        if redis_client:
            redis_client.set("key", "value", ex=300)  # Cache for 5 minutes
            value = redis_client.get("key")
        else:
            # Fallback to database or skip caching
            pass
    """
    if redis_client is None:
        logger.warning("⚠️ Redis is not available. Cache operations will be skipped.")
        return None
    
    # CRITICAL: Test connection before returning
    try:
        redis_client.ping()
        return redis_client
    except (redis.ConnectionError, redis.TimeoutError) as e:
        logger.warning(f"⚠️ Redis connection lost: {e}. Cache operations will be skipped.")
        return None
    except Exception as e:
        logger.error(f"❌ Redis error: {e}", exc_info=True)
        return None

