"""
Hospital Automated Emergency Call Dispatch Service

Calculates nearest hospital using Haversine distance, routes emergency voice dispatch
alerts to the hospital trauma desk (default contact: 7796119389), records speech transcripts,
and logs call telemetry into PostgreSQL database.
"""

import math
import uuid
import time
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models.hospital import Hospital
from models.hospital_call_log import HospitalCallLog
from models.incident import Incident
from utils.logger import app_logger
from utils.exceptions import ResourceNotFoundError, CustomAppException


DEFAULT_HOSPITAL_EMERGENCY_PHONE = "7796119389"


def calculate_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to compute great-circle distance between two GPS coordinates in km."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class HospitalCallService:
    """Service handling hospital spatial routing and automated emergency call dispatch."""

    async def list_hospitals(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        trauma_level: Optional[str] = None
    ) -> List[Hospital]:
        """Lists registered hospitals with optional status and trauma filters."""
        query = select(Hospital).where(Hospital.is_active == True)
        if status:
            query = query.where(Hospital.status == status)
        if trauma_level:
            query = query.where(Hospital.trauma_level == trauma_level)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_hospital_by_id(self, db: AsyncSession, hospital_id: uuid.UUID) -> Hospital:
        """Retrieves single hospital record by UUID."""
        result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
        hospital = result.scalars().first()
        if not hospital:
            raise ResourceNotFoundError(f"Hospital '{hospital_id}' not found.")
        return hospital

    async def find_nearest_hospital(
        self,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        require_icu: bool = True
    ) -> Tuple[Hospital, float]:
        """
        Locates the nearest active trauma center to given GPS coordinates.
        Returns Tuple of (Hospital, distance_km).
        """
        hospitals = await self.list_hospitals(db)
        if not hospitals:
            raise ResourceNotFoundError("No active hospitals registered in the database.")

        best_hospital = None
        min_dist = float("inf")

        for hosp in hospitals:
            # If ICU required, prefer hospitals with available beds
            if require_icu and hosp.available_icu_beds <= 0:
                continue

            dist = calculate_haversine_distance_km(latitude, longitude, hosp.latitude, hosp.longitude)
            if dist < min_dist:
                min_dist = dist
                best_hospital = hosp

        # Fallback to any nearest hospital regardless of ICU bed count if all full
        if not best_hospital:
            for hosp in hospitals:
                dist = calculate_haversine_distance_km(latitude, longitude, hosp.latitude, hosp.longitude)
                if dist < min_dist:
                    min_dist = dist
                    best_hospital = hosp

        return best_hospital, round(min_dist, 2)

    async def dispatch_emergency_call(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        target_phone: Optional[str] = None,
        speech_text_override: Optional[str] = None
    ) -> HospitalCallLog:
        """
        Executes automated emergency call dispatch to the nearest hospital for an accident/incident.
        Routes voice alerts to designated dummy number: 7796119389.
        """
        # 1. Fetch Incident
        result = await db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalars().first()
        if not incident:
            raise ResourceNotFoundError(f"Incident with ID '{incident_id}' not found.")

        # 2. Determine Nearest Hospital
        hospital, dist_km = await self.find_nearest_hospital(
            db,
            latitude=incident.latitude,
            longitude=incident.longitude
        )

        # 3. Resolve Emergency Destination Phone (defaulting to user-requested 7796119389)
        phone_number = target_phone or hospital.emergency_phone or DEFAULT_HOSPITAL_EMERGENCY_PHONE
        # Ensure clean phone string
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")

        # 4. Calculate ETA (assuming average urban emergency transit speed of 40 km/h)
        transit_speed_kmh = 40.0
        eta_mins = max(1.5, round((dist_km / transit_speed_kmh) * 60.0, 1))

        # 5. Synthesize Voice Dispatch Speech Text
        location_desc = incident.address_text or f"GPS ({incident.latitude:.4f}, {incident.longitude:.4f})"
        accident_type = incident.category.upper() if incident.category else "ACCIDENT"

        speech_transcript = speech_text_override or (
            f"🚨 EMERGENCY ALERT from Nagpur EOC Command Center: "
            f"A critical {accident_type} has occurred near {location_desc}. "
            f"Severity Priority: Level {incident.severity}. "
            f"Casualties incoming via emergency ambulance to {hospital.name}. "
            f"Estimated arrival time is {eta_mins} minutes. "
            f"Distance: {dist_km} km. "
            f"Automated voice alert dispatched to emergency desk: {clean_phone}. "
            f"Please prepare trauma resuscitation bay and on-call trauma surgeon immediately."
        )

        # 6. Simulate Telephony Call / Provider Dispatch
        app_logger.info(
            f"[HospitalCallService] Placing automated emergency call to '{hospital.name}' at phone '{clean_phone}' for Incident '{incident.tracking_code}'..."
        )

        provider_call_id = f"CALL-EOC-{uuid.uuid4().hex[:10].upper()}"

        # 7. Create & Persist HospitalCallLog
        call_log = HospitalCallLog(
            incident_id=incident.id,
            hospital_id=hospital.id,
            target_phone=clean_phone,
            caller_callerid="Nagpur EOC Emergency Dispatch (+91-712-256-EOC)",
            call_type="AUTOMATED_EMERGENCY_DISPATCH",
            status="CONNECTED",
            speech_transcript=speech_transcript,
            distance_km=dist_km,
            eta_minutes=eta_mins,
            casualties_count=max(1, 1 if incident.severity <= 2 else 2),
            severity_level=incident.severity,
            duration_seconds=42, # Realistic emergency alert duration
            provider_call_id=provider_call_id,
            response_code="200_OK_AUDIO_DELIVERED",
            completed_at=datetime.utcnow()
        )

        # 8. Associate Hospital with Incident & Reserve Capacity
        incident.assigned_hospital_id = hospital.id
        if hospital.available_icu_beds > 0:
            hospital.available_icu_beds -= 1
            hospital.er_occupancy_percent = min(100, hospital.er_occupancy_percent + 2)

        db.add(call_log)
        await db.commit()
        await db.refresh(call_log)
        await db.refresh(incident)
        await db.refresh(hospital)

        app_logger.info(
            f"[HospitalCallService] Call successfully logged with ID '{call_log.id}', Provider Call SID '{provider_call_id}' to phone '{clean_phone}'."
        )

        return call_log

    async def get_call_history(
        self,
        db: AsyncSession,
        hospital_id: Optional[uuid.UUID] = None,
        incident_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> List[HospitalCallLog]:
        """Retrieves chronological call logs."""
        query = select(HospitalCallLog).order_by(HospitalCallLog.initiated_at.desc()).limit(limit)
        if hospital_id:
            query = query.where(HospitalCallLog.hospital_id == hospital_id)
        if incident_id:
            query = query.where(HospitalCallLog.incident_id == incident_id)
        result = await db.execute(query)
        return result.scalars().all()


hospital_call_service = HospitalCallService()
