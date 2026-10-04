"""
Incident Domain & CRUD Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from uuid import UUID, uuid4
import random
from models.incident import Incident
from schemas.incident import IncidentCreate, IncidentStatusUpdate
from utils.exceptions import ResourceNotFoundError

class IncidentService:
    """Handles emergency incident reporting, queries, and status updates."""

    def generate_tracking_code(self) -> str:
        """Generates human-readable, collision-safe tracking code e.g. EMG-2026-A1B2C3D4."""
        return f"EMG-2026-{uuid4().hex[:8].upper()}"

    async def create_incident(
        self, 
        db: AsyncSession, 
        incident_in: IncidentCreate, 
        reporter_id: Optional[UUID] = None
    ) -> Incident:
        """Create new emergency incident report."""
        db_incident = Incident(
            tracking_code=self.generate_tracking_code(),
            reporter_id=reporter_id,
            description=incident_in.description,
            latitude=incident_in.latitude,
            longitude=incident_in.longitude,
            address_text=incident_in.address_text,
            category="other",
            severity=3,
            status="reported"
        )
        db.add(db_incident)
        await db.commit()
        await db.refresh(db_incident)
        return db_incident

    async def get_by_id(self, db: AsyncSession, incident_id: UUID) -> Incident:
        """Retrieve single incident by UUID."""
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalars().first()
        if not incident:
            raise ResourceNotFoundError(f"Incident with ID '{incident_id}' not found.")
        return incident

    async def list_incidents(
        self, 
        db: AsyncSession, 
        status: Optional[str] = None, 
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Incident]:
        """List incidents with optional status and category filters."""
        query = select(Incident).order_by(desc(Incident.created_at)).limit(limit)
        if status:
            query = query.where(Incident.status == status)
        if category:
            query = query.where(Incident.category == category)
            
        result = await db.execute(query)
        return result.scalars().all()

    async def update_status(self, db: AsyncSession, incident_id: UUID, status_in: IncidentStatusUpdate) -> Incident:
        """Update operational status of an incident."""
        incident = await self.get_by_id(db, incident_id)
        incident.status = status_in.status
        await db.commit()
        await db.refresh(incident)
        return incident

incident_service = IncidentService()
