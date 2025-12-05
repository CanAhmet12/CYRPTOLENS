"""
Shared database connection module for CryptoLens backend services.
Uses SQLAlchemy for PostgreSQL connections.
CRITICAL: Includes connection error handling and transaction management.
"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from contextlib import contextmanager
from .config import settings

logger = logging.getLogger(__name__)

# Create database engine with connection pooling and error handling
try:
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # CRITICAL: Verify connections before using
        pool_recycle=3600,  # CRITICAL: Recycle connections after 1 hour
        echo=settings.DEBUG,  # Log SQL queries in debug mode
        connect_args={
            "connect_timeout": 10,  # CRITICAL: Connection timeout
            "application_name": "cryptolens_backend",  # CRITICAL: Application name for monitoring
        }
    )
    
    # CRITICAL: Test connection on initialization
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}", exc_info=True)
        raise
    
except Exception as e:
    logger.critical(f"❌ Failed to create database engine: {e}", exc_info=True)
    raise

# CRITICAL: Connection pool event listeners for monitoring
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set connection-level settings."""
    pass  # PostgreSQL doesn't need pragma, but we can add connection-level settings here

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkout."""
    if settings.DEBUG:
        logger.debug("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log connection checkin."""
    if settings.DEBUG:
        logger.debug("Database connection returned to pool")

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get database session.
    FIX: Removed automatic commit - services handle their own commits to avoid double commits.
    CRITICAL: Includes error handling and automatic rollback on exception.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Service methods handle their own commits
            ...
    """
    db = SessionLocal()
    try:
        yield db
        # FIX: Don't auto-commit - services handle their own commits
        # This prevents double commits when services call db.commit() manually
    except SQLAlchemyError as e:
        db.rollback()  # CRITICAL: Rollback on error
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    except Exception as e:
        db.rollback()  # CRITICAL: Rollback on any error
        logger.error(f"Unexpected error in database session: {e}", exc_info=True)
        raise
    finally:
        db.close()  # CRITICAL: Always close session


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    CRITICAL: Use this for manual transaction management.
    
    Usage:
        with get_db_context() as db:
            # Database operations
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in context: {e}", exc_info=True)
        raise
    finally:
        db.close()

