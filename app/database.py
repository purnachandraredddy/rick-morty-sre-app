"""Database connection and session management."""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import structlog

from app.config import settings
from app.models import Base

logger = structlog.get_logger()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    echo=settings.debug,
    poolclass=StaticPool if "sqlite" in settings.database_url else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
)


async def create_tables():
    """Create database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


async def drop_tables():
    """Drop database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error("Failed to drop database tables", error=str(e))
        raise


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with get_db_session() as session:
        yield session


async def check_db_connection() -> bool:
    """Check database connection health."""
    try:
        async with get_db_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


async def close_db_connection():
    """Close database connection."""
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error("Failed to close database connection", error=str(e))
