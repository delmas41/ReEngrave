"""
SQLAlchemy async engine setup for ReEngrave.
Uses SQLite with aiosqlite driver by default.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.models import Base

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./reengrave.db"
)

# ---------------------------------------------------------------------------
# Engine & Session factory
# ---------------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set True for SQL query logging during development
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session; close on completion."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------


async def create_all_tables() -> None:
    """Create all tables defined in Base.metadata.
    Called at application startup via FastAPI lifespan.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
