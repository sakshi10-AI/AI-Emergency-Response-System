"""
Responder Units API Router

Handles responder vehicle registration, listing, GPS telemetry pings, and status updates.
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from database.connection import get_db
from schemas.responder import ResponderUnitCreate, ResponderUnitResponse, ResponderUnitTelemetry, ResponderUnitStatusUpdate
from services.unit_service import unit_service
from authentication.rbac import require_roles
from models.user import User

router = APIRouter(prefix="/api/v1/units", tags=["Responder Units"])

@router.post("/", response_model=ResponderUnitResponse, status_code=status.HTTP_201_CREATED, summary="Register a new responder unit")
async def register_unit(
    unit_in: ResponderUnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"]))
):
    """Registers a new emergency response unit (Admins only)."""
    return await unit_service.create_unit(db, unit_in)

@router.get("/", response_model=List[ResponderUnitResponse], summary="List responder units")
async def list_units(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["dispatcher", "admin", "responder"]))
):
    """Lists responder units with optional status filtering."""
    return await unit_service.list_units(db, status=status_filter)

@router.post("/{unit_id}/telemetry", response_model=ResponderUnitResponse, summary="Update unit GPS location telemetry")
async def update_telemetry(
    unit_id: UUID,
    telemetry: ResponderUnitTelemetry,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["responder", "dispatcher", "admin"]))
):
    """Pings current GPS coordinates for a responder unit."""
    return await unit_service.update_telemetry(db, unit_id, telemetry)

@router.patch("/{unit_id}/status", response_model=ResponderUnitResponse, summary="Update unit operational status")
async def update_unit_status(
    unit_id: UUID,
    status_in: ResponderUnitStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["responder", "dispatcher", "admin"]))
):
    """Updates operational availability status for a unit."""
    return await unit_service.update_status(db, unit_id, status_in)
