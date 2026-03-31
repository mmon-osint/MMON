"""
MMON — Database engine e session management (async).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.config import get_settings


class Base(DeclarativeBase):
    """Base class per tutti i modelli SQLAlchemy."""
    pass


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency FastAPI che fornisce una sessione DB.
    Yield pattern: commit/rollback gestito dal chiamante.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
