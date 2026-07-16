"""Database connection and session management.

Relocated from app/db.py: that flat module collided with this app/db/
package (added alongside it for base.py) — a module and a package can't
share a name, and the package was silently winning, making engine/
get_db/init_db/close_db unreachable. CODING_STANDARDS.md's own documented
layout already calls for db/session.py + db/base.py, so this move matches
the intended structure rather than working around the collision.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.

    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables). Dev/test convenience only —
    production schema changes go through Alembic migrations (T-203)."""
    # Import app.models first so Organization/User/Document/Review/Finding/
    # AuditLog are registered on Base.metadata before create_all runs.
    import app.models  # noqa: F401
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database closed")
