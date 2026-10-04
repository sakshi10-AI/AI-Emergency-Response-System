"""
FastAPI Backend Main Application Entrypoint

Wires together database initialization, CORS, exception handlers, and API routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from config.settings import settings
from database.connection import init_db
from utils.exceptions import CustomAppException
from middleware.error_handler import (
    custom_app_exception_handler,
    validation_exception_handler,
    global_exception_handler
)
from routers import auth, incidents, units, health, agents_router, hospitals, reports, notifications, websockets, vision_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown hooks."""
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready AI Emergency Response System API with Multi-Agent Triage, JWT Auth, and Real-time Telemetry.",
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(CustomAppException, custom_app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(incidents.router)
app.include_router(units.router)
app.include_router(hospitals.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(agents_router.router)
app.include_router(websockets.router)
app.include_router(vision_router.router)


