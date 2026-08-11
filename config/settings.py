"""
Production Configuration Settings

Uses Pydantic BaseSettings for strong typing, default values, and environment variable loading.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Emergency Response System API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Server Host & Port
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # JWT Authentication Parameters
    SECRET_KEY: str = "super_secret_jwt_key_change_in_production_984123847"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 Hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database Settings (PostgreSQL default, SQLite fallback capability for unit tests)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_password"
    POSTGRES_DB: str = "ai_emergency_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = "postgresql+asyncpg://postgres:postgres_password@localhost:5432/ai_emergency_db"
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    # Google Gemini AI Settings
    GEMINI_API_KEY: str = ""
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    ADVANCED_GEMINI_MODEL: str = "gemini-2.5-pro"

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
