"""
Health & System Status API Router

Provides status endpoints for monitoring backend operational status, DB latency, and settings.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.connection import get_db
from config.settings import settings

router = APIRouter(tags=["Health"])

@router.get("/health", status_code=status.HTTP_200_OK, summary="Basic health check endpoint")
@router.get("/api/v1/health", status_code=status.HTTP_200_OK, summary="API v1 health check endpoint", include_in_schema=False)
@router.get("/api/v1/health/", status_code=status.HTTP_200_OK, summary="API v1 trailing slash health check", include_in_schema=False)
async def health_check():
    """Simple status check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@router.get("/health/db", status_code=status.HTTP_200_OK, summary="Database connectivity check")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Verifies active connectivity to PostgreSQL database."""
    try:
        result = await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "query_result": result.scalar()}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
