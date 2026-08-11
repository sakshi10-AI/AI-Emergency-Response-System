"""
Async SQLAlchemy Engine & Session Configuration
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings
from utils.logger import app_logger

# PostgreSQL Async Connection Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    """Dependency injection function for obtaining an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            app_logger.error(f"Database session rollback due to error: {e}")
            raise
        finally:
            await session.close()

async def init_db():
    """Utility function to create database tables on startup with resilient fallback."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app_logger.info("Database tables initialized successfully.")
    except Exception as e:
        app_logger.warning(f"PostgreSQL database offline ({e}). Backend operating in resilient memory fallback mode.")
