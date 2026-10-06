"""
Pytest Test Fixtures & Test Setup Configuration
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.connection import Base, get_db
from backend.main import app

# In-memory SQLite for high-speed isolated backend tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_database():
    """Creates fresh schema for every test function and drops on teardown."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from models.hospital import Hospital
    async with TestingSessionLocal() as session:
        hosp = Hospital(
            code="HOSP-GMCH-01",
            name="Government Medical College & Hospital (GMCH) Nagpur",
            address="Medical Square, Hanuman Nagar, Nagpur, Maharashtra 440003",
            city="Nagpur",
            latitude=21.1278,
            longitude=79.0965,
            emergency_phone="7796119389",
            alternate_phone="0712-2744671",
            trauma_level="Level I",
            total_emergency_beds=80,
            available_emergency_beds=20,
            total_icu_beds=40,
            available_icu_beds=10,
            status="OPEN",
            is_active=True
        )
        session.add(hosp)
        await session.commit()

    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def override_get_db():
    """Dependency override injecting test database session."""
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="function")
async def client():
    """Async HTTP test client fixture using ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
