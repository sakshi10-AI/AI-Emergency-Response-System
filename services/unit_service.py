"""
Responder Unit Domain & Telemetry Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from models.responder_unit import ResponderUnit
from schemas.responder import ResponderUnitCreate, ResponderUnitTelemetry, ResponderUnitStatusUpdate
from utils.exceptions import ResourceNotFoundError, CustomAppException

class UnitService:
    """Manages responder units, GPS location telemetry, and availability."""

    async def create_unit(self, db: AsyncSession, unit_in: ResponderUnitCreate) -> ResponderUnit:
        """Register a new responder unit."""
        existing = await db.execute(select(ResponderUnit).where(ResponderUnit.call_sign == unit_in.call_sign))
        if existing.scalars().first():
            raise CustomAppException(f"Unit call sign '{unit_in.call_sign}' already registered", status_code=400)

        db_unit = ResponderUnit(
            call_sign=unit_in.call_sign,
            unit_type=unit_in.unit_type,
            current_lat=unit_in.current_lat,
            current_lon=unit_in.current_lon,
            status="available"
        )
        db.add(db_unit)
        await db.commit()
        await db.refresh(db_unit)
        return db_unit

    async def get_by_id(self, db: AsyncSession, unit_id: UUID) -> ResponderUnit:
        """Retrieve unit by UUID."""
        result = await db.execute(select(ResponderUnit).where(ResponderUnit.id == unit_id))
        unit = result.scalars().first()
        if not unit:
            raise ResourceNotFoundError(f"Responder unit '{unit_id}' not found")
        return unit

    async def list_units(self, db: AsyncSession, status: Optional[str] = None) -> List[ResponderUnit]:
        """List all responder units."""
        query = select(ResponderUnit)
        if status:
            query = query.where(ResponderUnit.status == status)
        result = await db.execute(query)
        return result.scalars().all()

    async def update_telemetry(self, db: AsyncSession, unit_id: UUID, telemetry: ResponderUnitTelemetry) -> ResponderUnit:
        """Update GPS latitude/longitude ping for unit."""
        unit = await self.get_by_id(db, unit_id)
        unit.current_lat = telemetry.current_lat
        unit.current_lon = telemetry.current_lon
        await db.commit()
        await db.refresh(unit)
        return unit

    async def update_status(self, db: AsyncSession, unit_id: UUID, status_in: ResponderUnitStatusUpdate) -> ResponderUnit:
        """Update unit availability status."""
        unit = await self.get_by_id(db, unit_id)
        unit.status = status_in.status
        await db.commit()
        await db.refresh(unit)
        return unit

unit_service = UnitService()
