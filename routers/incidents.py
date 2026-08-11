"""
Incidents API Router

Handles emergency reporting, incident queries, status updates, and dispatch workflow triggers
with Role-Based Access Control (Admin, Police, Hospital, Dispatcher, Viewer).
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from schemas.incident import IncidentCreate, IncidentResponse, IncidentStatusUpdate
from services.incident_service import incident_service
from authentication.rbac import get_current_user, get_optional_current_user, require_roles, Role
from models.user import User

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, summary="Report a new emergency incident")
async def report_incident(
    incident_in: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Submits a new emergency report (accessible by citizens or authenticated roles)."""
    reporter_id = current_user.id if current_user else None
    return await incident_service.create_incident(db, incident_in, reporter_id=reporter_id)


@router.get("/", response_model=List[IncidentResponse], summary="List all emergency incidents")
async def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    category_filter: Optional[str] = Query(None, alias="category", description="Filter by category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([Role.ADMIN, Role.DISPATCHER, Role.POLICE, Role.HOSPITAL, Role.VIEWER]))
):
    """Lists incidents for authorized roles."""
    return await incident_service.list_incidents(db, status=status_filter, category=category_filter)


@router.get("/{incident_id}", response_model=IncidentResponse, summary="Get incident by UUID")
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves detailed information for a specific emergency incident."""
    return await incident_service.get_by_id(db, incident_id)


@router.patch("/{incident_id}/status", response_model=IncidentResponse, summary="Update incident status")
async def update_incident_status(
    incident_id: UUID,
    status_in: IncidentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([Role.ADMIN, Role.DISPATCHER, Role.POLICE]))
):
    """Updates the operational status of an incident (Admin, Dispatcher, Police only)."""
    return await incident_service.update_status(db, incident_id, status_in)


@router.post("/{incident_id}/approve", summary="Approve dispatch plan")
async def approve_dispatch(
    incident_id: str,
    current_user: User = Depends(require_roles([Role.ADMIN, Role.DISPATCHER]))
):
    """Submits supervisor approval for a pending dispatch plan (Admin & Dispatcher only)."""
    return {"status": "APPROVED", "incident_id": incident_id, "approved_by": current_user.email}
