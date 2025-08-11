from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Async Engine for FastAPI
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_timeout=30,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# Sync Engine for Alembic migrations
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
)

# Sync Session Factory (for migrations and Celery tasks)
SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Dependency for async database sessions
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session.
    This will be used in FastAPI route dependencies.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

# Function for sync sessions (Celery tasks)
def get_sync_session():
    """
    Get synchronous database session for Celery tasks.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Sync database session error: {e}")
        raise
    finally:
        session.close()

# Database utility functions
async def init_db() -> None:
    """Initialize database - create all tables"""
    try:
        # Import all models to ensure they are registered
        from app.models import client, asset, allocation, daily_return, user
        
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def close_db() -> None:
    """Close database connections"""
    try:
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

# Health check function
async def check_db_health() -> bool:
    """Check if database is healthy"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False