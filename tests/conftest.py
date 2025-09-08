"""Test configuration and fixtures."""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models import Base
from app.config import settings
from app.cache import cache


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Override database dependency for testing."""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Set up test database."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Create a test database session."""
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # Clean up all data after each test
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def client(setup_database):
    """Create test client."""
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Clean up override
    app.dependency_overrides.clear()


@pytest.fixture
def mock_rick_morty_data():
    """Mock Rick and Morty API data."""
    return {
        "info": {
            "count": 826,
            "pages": 42,
            "next": "https://rickandmortyapi.com/api/character?page=2",
            "prev": None
        },
        "results": [
            {
                "id": 1,
                "name": "Rick Sanchez",
                "status": "Alive",
                "species": "Human",
                "type": "",
                "gender": "Male",
                "origin": {
                    "name": "Earth (C-137)",
                    "url": "https://rickandmortyapi.com/api/location/1"
                },
                "location": {
                    "name": "Citadel of Ricks",
                    "url": "https://rickandmortyapi.com/api/location/3"
                },
                "image": "https://rickandmortyapi.com/api/character/avatar/1.jpeg",
                "episode": [
                    "https://rickandmortyapi.com/api/episode/1",
                    "https://rickandmortyapi.com/api/episode/2"
                ],
                "url": "https://rickandmortyapi.com/api/character/1",
                "created": "2017-11-04T18:48:46.250Z"
            },
            {
                "id": 2,
                "name": "Morty Smith",
                "status": "Alive",
                "species": "Human",
                "type": "",
                "gender": "Male",
                "origin": {
                    "name": "Earth (C-137)",
                    "url": "https://rickandmortyapi.com/api/location/1"
                },
                "location": {
                    "name": "Citadel of Ricks",
                    "url": "https://rickandmortyapi.com/api/location/3"
                },
                "image": "https://rickandmortyapi.com/api/character/avatar/2.jpeg",
                "episode": [
                    "https://rickandmortyapi.com/api/episode/1",
                    "https://rickandmortyapi.com/api/episode/2"
                ],
                "url": "https://rickandmortyapi.com/api/character/2",
                "created": "2017-11-04T18:50:21.651Z"
            }
        ]
    }


@pytest.fixture
def sample_character_data():
    """Sample character data for testing."""
    return {
        "id": 1,
        "name": "Rick Sanchez",
        "status": "Alive",
        "species": "Human",
        "type": "",
        "gender": "Male",
        "origin_name": "Earth (C-137)",
        "origin_url": "https://rickandmortyapi.com/api/location/1",
        "location_name": "Citadel of Ricks",
        "location_url": "https://rickandmortyapi.com/api/location/3",
        "image_url": "https://rickandmortyapi.com/api/character/avatar/1.jpeg",
        "episode_urls": '["https://rickandmortyapi.com/api/episode/1"]',
        "api_url": "https://rickandmortyapi.com/api/character/1",
    }


@pytest_asyncio.fixture(autouse=True)
async def setup_cache():
    """Set up cache for testing."""
    # Use test cache settings
    original_redis_url = settings.redis_url
    settings.redis_url = "redis://localhost:6379/15"  # Use test database
    
    cache_connected = False
    try:
        await cache.connect()
        cache_connected = True
    except Exception:
        # Cache not available, disable cache for tests
        cache._connected = False
        pass
    
    yield
    
    # Clean up
    if cache_connected:
        try:
            await cache.clear_pattern("*")
            await cache.disconnect()
        except Exception:
            pass
    
    # Restore original settings
    settings.redis_url = original_redis_url
