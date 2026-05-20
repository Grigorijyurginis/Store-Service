import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Must be set before app imports so config.py reads the right DATABASE_URL
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402  — also registers ORM models via its own import

_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Truncate all tables after each test to ensure isolation."""
    yield
    async with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
