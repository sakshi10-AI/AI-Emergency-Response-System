"""
Async SQLAlchemy Engine & Session Configuration
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings
from utils.logger import app_logger

# Database URL & Engine Configuration
db_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./ai_emergency.db"
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}
if "sqlite" not in db_url:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True
    })

engine = create_async_engine(db_url, **engine_kwargs)

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
        
        # Auto-seed initial records (hospitals, users, fleet) if DB is empty
        try:
            from database.seed_data import seed_database
            await seed_database(force_reseed=False)
        except Exception as seed_err:
            app_logger.warning(f"Database auto-seeding skipped: {seed_err}")
    except Exception as e:
        app_logger.warning(f"Database initialization fallback ({e}). Operating in resilient fallback mode.")
