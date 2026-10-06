"""
Database Seeding & Schema Generator Script

Initializes the complete database schema (PostgreSQL / SQLite) and populates
production-ready seed data for the Nagpur Emergency Operations Center (EOC):
- 5 User profiles with hashed bcrypt passwords
- 5 Nagpur Trauma Centers with emergency desk phone (7796119389)
- 5 EMS & Responder fleet units
- Realistic emergency incidents with automated hospital voice dispatch calls logged
- Public alerts and dispatch assignments

Run standalone via:
    python -m database.seed_data
or
    python database/seed_data.py
"""

import sys
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from sqlalchemy import select
from database.connection import engine, AsyncSessionLocal, Base
from authentication.jwt import get_password_hash
from models import (
    User,
    Hospital,
    HospitalCallLog,
    ResponderUnit,
    Incident,
    DispatchAssignment,
    PublicAlert,
    AgentAuditLog,
    IncidentReport
)
from utils.logger import app_logger

TARGET_DUMMY_PHONE = "7796119389"


async def seed_database(force_reseed: bool = False):
    """Generates all database tables and seeds initial operational data."""
    app_logger.info("Initializing database schema...")

    async with engine.begin() as conn:
        if force_reseed:
            app_logger.warning("Dropping all existing tables for clean reseed...")
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    app_logger.info("Database schema verified. Populating seed records...")

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_user = await session.execute(select(User).limit(1))
        if existing_user.scalars().first() and not force_reseed:
            app_logger.info("Database is already seeded with records. Skipping re-population.")
            return

        # =====================================================================
        # 1. Seed Users (Admin, Dispatcher, Police, Hospital, Citizen)
        # =====================================================================
        app_logger.info("Seeding system users...")
        users = [
            User(
                email="admin@eoc.gov",
                hashed_password=get_password_hash("admin123"),
                full_name="Chief Administrator Sharma",
                role="admin",
                is_active=True
            ),
            User(
                email="dispatcher@eoc.gov",
                hashed_password=get_password_hash("dispatch123"),
                full_name="Senior Dispatcher Priya Patel",
                role="dispatcher",
                is_active=True
            ),
            User(
                email="police@eoc.gov",
                hashed_password=get_password_hash("police123"),
                full_name="Inspector Rajesh Deshmukh",
                role="police",
                is_active=True
            ),
            User(
                email="hospital@gmch.gov",
                hashed_password=get_password_hash("hosp123"),
                full_name="Dr. Sunita Kulkarni (GMCH Trauma In-charge)",
                role="hospital",
                is_active=True
            ),
            User(
                email="citizen@eoc.gov",
                hashed_password=get_password_hash("citizen123"),
                full_name="Rahul Verma (Citizen Reporter)",
                role="citizen",
                is_active=True
            )
        ]
        session.add_all(users)
        await session.flush()

        admin_user = users[0]
        dispatcher_user = users[1]
        citizen_user = users[4]

        # =====================================================================
        # 2. Seed Nagpur Trauma Centers & Hospitals (Phone: 7796119389)
        # =====================================================================
        app_logger.info("Seeding Nagpur regional trauma hospitals...")
        hospitals = [
            Hospital(
                code="HOSP-NGP-01",
                name="Government Medical College & Hospital (GMCH) Nagpur",
                emergency_phone=TARGET_DUMMY_PHONE,
                alternate_phone="+91-712-2744654",
                trauma_level="Level I",
                address="Medical Square, Ajni Road, Medical College Campus, Nagpur 440003",
                city="Nagpur",
                latitude=21.1367,
                longitude=79.0995,
                total_icu_beds=60,
                available_icu_beds=14,
                total_emergency_beds=120,
                available_emergency_beds=32,
                er_occupancy_percent=78,
                specialties=["Trauma Resuscitation", "Burn Unit", "Neurosurgery", "Cardio-Thoracic", "Orthopedics"],
                status="OPEN",
                is_active=True
            ),
            Hospital(
                code="HOSP-NGP-02",
                name="Wockhardt Super Speciality Hospital Nagpur",
                emergency_phone=TARGET_DUMMY_PHONE,
                alternate_phone="+91-712-6624444",
                trauma_level="Level II",
                address="1643, North Ambazari Road, Shankar Nagar Square, Nagpur 440010",
                city="Nagpur",
                latitude=21.1290,
                longitude=79.0760,
                total_icu_beds=30,
                available_icu_beds=8,
                total_emergency_beds=60,
                available_emergency_beds=16,
                er_occupancy_percent=68,
                specialties=["Hazmat Decontamination", "Interventional Cardiology", "Critical Care", "General Surgery"],
                status="OPEN",
                is_active=True
            ),
            Hospital(
                code="HOSP-NGP-03",
                name="Orange City Hospital & Research Institute",
                emergency_phone=TARGET_DUMMY_PHONE,
                alternate_phone="+91-712-6634800",
                trauma_level="Level II",
                address="Plot No. 19, Khamla Road, Veer Savarkar Square, Nagpur 440015",
                city="Nagpur",
                latitude=21.1180,
                longitude=79.0620,
                total_icu_beds=25,
                available_icu_beds=6,
                total_emergency_beds=50,
                available_emergency_beds=12,
                er_occupancy_percent=75,
                specialties=["Multi-trauma", "Cardiology", "Pediatric Emergency"],
                status="OPEN",
                is_active=True
            ),
            Hospital(
                code="HOSP-NGP-04",
                name="All India Institute of Medical Sciences (AIIMS) Nagpur",
                emergency_phone=TARGET_DUMMY_PHONE,
                alternate_phone="+91-712-2821000",
                trauma_level="Level I",
                address="Plot No. 2, Sector 20, MIHAN, Nagpur, Maharashtra 441108",
                city="Nagpur",
                latitude=21.0480,
                longitude=79.0270,
                total_icu_beds=80,
                available_icu_beds=22,
                total_emergency_beds=150,
                available_emergency_beds=45,
                er_occupancy_percent=65,
                specialties=["Advanced Trauma Life Support", "Neurosurgery", "Toxicology & Poison Control"],
                status="OPEN",
                is_active=True
            ),
            Hospital(
                code="HOSP-NGP-05",
                name="Lata Mangeshkar Hospital Nagpur",
                emergency_phone=TARGET_DUMMY_PHONE,
                alternate_phone="+91-7104-665000",
                trauma_level="Level III",
                address="Digdoh Hills, Hingna Road, Nagpur 440019",
                city="Nagpur",
                latitude=21.1520,
                longitude=79.0180,
                total_icu_beds=20,
                available_icu_beds=5,
                total_emergency_beds=40,
                available_emergency_beds=9,
                er_occupancy_percent=70,
                specialties=["General Trauma", "Orthopedic Surgery", "Emergency Medicine"],
                status="OPEN",
                is_active=True
            )
        ]
        session.add_all(hospitals)
        await session.flush()

        gmch_hospital = hospitals[0]
        wockhardt_hospital = hospitals[1]

        # =====================================================================
        # 3. Seed Responder Fleet Units
        # =====================================================================
        app_logger.info("Seeding responder units...")
        units = [
            ResponderUnit(
                call_sign="Nagpur Medic 101",
                unit_type="ALS Ambulance",
                status="available",
                current_lat=21.1410,
                current_lon=79.0820,
                assigned_user_id=dispatcher_user.id
            ),
            ResponderUnit(
                call_sign="Nagpur Medic 102",
                unit_type="BLS Ambulance",
                status="available",
                current_lat=21.1530,
                current_lon=79.1020,
                assigned_user_id=dispatcher_user.id
            ),
            ResponderUnit(
                call_sign="Nagpur Medic 103",
                unit_type="MICU Ambulance",
                status="available",
                current_lat=21.0120,
                current_lon=79.0200,
                assigned_user_id=dispatcher_user.id
            ),
            ResponderUnit(
                call_sign="Police PCR-01",
                unit_type="Patrol Vehicle",
                status="available",
                current_lat=21.1480,
                current_lon=79.0850,
                assigned_user_id=admin_user.id
            ),
            ResponderUnit(
                call_sign="Fire Tender 01",
                unit_type="Hazmat / Fire Engine",
                status="available",
                current_lat=21.1620,
                current_lon=79.0720,
                assigned_user_id=admin_user.id
            )
        ]
        session.add_all(units)
        await session.flush()

        medic_101 = units[0]

        # =====================================================================
        # 4. Seed Incidents (Accident, Industrial Fire, Cardiac)
        # =====================================================================
        app_logger.info("Seeding active emergency incidents...")
        incident_accident = Incident(
            tracking_code="EMG-2026-NAGP0001",
            reporter_id=citizen_user.id,
            category="accident",
            severity=1,
            description="Major two-wheeler and SUV collision with 2 severely injured casualties near Wardha Road & Ajni Square.",
            status="dispatched",
            latitude=21.1458,
            longitude=79.0882,
            address_text="Wardha Road near Ajni Square, Nagpur, Maharashtra",
            triage_summary="Level 1 Critical Priority: Severe blunt trauma and bleeding. Immediate ALS dispatch and trauma center alert required.",
            threat_assessment="Active traffic congestion; green corridor preemption requested on Wardha Road.",
            assigned_hospital_id=gmch_hospital.id
        )

        incident_fire = Incident(
            tracking_code="EMG-2026-NAGP0002",
            reporter_id=citizen_user.id,
            category="fire",
            severity=2,
            description="Electrical transformer fire and smoke plume at Butibori MIDC Gate No. 2.",
            status="triaged",
            latitude=21.0120,
            longitude=79.0200,
            address_text="Plot No. 45, Butibori MIDC, Nagpur",
            triage_summary="Level 2 Urgent: Commercial electrical fire. Fire tender dispatched with foam unit.",
            threat_assessment="Dense smoke drift towards nearby warehouse.",
            assigned_hospital_id=wockhardt_hospital.id
        )

        session.add_all([incident_accident, incident_fire])
        await session.flush()

        # =====================================================================
        # 5. Seed Dispatch Assignments
        # =====================================================================
        app_logger.info("Seeding dispatch assignments...")
        dispatch = DispatchAssignment(
            incident_id=incident_accident.id,
            unit_id=medic_101.id,
            status="dispatched",
            assigned_by_agent=True,
            agent_reasoning="Nearest Advanced Life Support unit (Nagpur Medic 101, 1.4 km away). ETA 4.2 minutes."
        )
        session.add(dispatch)

        # =====================================================================
        # 6. Seed Hospital Automated Voice Call Log (To: 7796119389)
        # =====================================================================
        app_logger.info(f"Seeding automated emergency call dispatch log (Phone: {TARGET_DUMMY_PHONE})...")
        call_log = HospitalCallLog(
            incident_id=incident_accident.id,
            hospital_id=gmch_hospital.id,
            target_phone=TARGET_DUMMY_PHONE,
            caller_callerid="Nagpur EOC Emergency Dispatch (+91-712-256-EOC)",
            call_type="AUTOMATED_EMERGENCY_DISPATCH",
            status="COMPLETED",
            speech_transcript=(
                f"🚨 EMERGENCY ALERT from Nagpur EOC: Major vehicle collision near Wardha Road & Ajni Square. "
                f"Severity Level 1. 2 casualties incoming to GMCH Nagpur via Nagpur Medic 101. "
                f"ETA: 4.2 minutes. Automated call routed to emergency desk: {TARGET_DUMMY_PHONE}. "
                f"Please reserve Trauma Bay 1 and alert neurosurgeon."
            ),
            distance_km=2.1,
            eta_minutes=4.2,
            casualties_count=2,
            severity_level=1,
            duration_seconds=46,
            provider_call_id="CALL-EOC-NAGPUR-7796119389",
            response_code="200_OK_AUDIO_DELIVERED",
            completed_at=datetime.now(timezone.utc)
        )
        session.add(call_log)

        # =====================================================================
        # 7. Seed Public Alerts
        # =====================================================================
        alert = PublicAlert(
            incident_id=incident_accident.id,
            title="TRAFFIC & EMERGENCY ALERT: Wardha Road",
            message="Traffic diversion active near Ajni Square due to an ongoing accident response. Emergency green corridor in effect.",
            severity="CRITICAL"
        )
        session.add(alert)

        await session.commit()
        app_logger.info("✅ Database successfully seeded with 5 users, 5 Nagpur hospitals, 5 fleet units, 2 active incidents, and automated call logs!")


def main():
    """CLI Entrypoint for running seed generator script."""
    force = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(seed_database(force_reseed=force))


if __name__ == "__main__":
    main()
