"""
Unit & Integration Tests for PostgreSQL Database ORM Models & Persistence

Tests:
- User Model (Password hashing, role assignment, active flag)
- Incident Model (Severity, status, location coordinates)
- ResponderUnit Model (Unit type, call sign, status, location)
- DispatchAssignment Model (Incident-to-Unit dispatch mapping)
- PublicAlert Model (Alert broadcast data)
- AgentAuditLog Model (Chronological agent execution logs)
- IncidentReport Model (PostgreSQL report persistence, JSON metadata)
"""

import pytest
import uuid
from models import (
    User,
    Incident,
    ResponderUnit,
    DispatchAssignment,
    PublicAlert,
    AgentAuditLog,
    IncidentReport,
    Hospital,
    HospitalCallLog
)


def test_user_model_instantiation():
    """Tests User SQLAlchemy model instantiation."""
    u_id = uuid.uuid4()
    user = User(
        id=u_id,
        email="dispatcher@eoc.gov",
        hashed_password="hashed_bcrypt_secret",
        full_name="Officer John",
        role="dispatcher",
        is_active=True
    )
    assert user.id == u_id
    assert user.email == "dispatcher@eoc.gov"
    assert user.role == "dispatcher"
    assert user.is_active is True


def test_incident_model_instantiation():
    """Tests Incident SQLAlchemy model instantiation."""
    inc_id = uuid.uuid4()
    inc = Incident(
        id=inc_id,
        tracking_code="TRK-8821",
        category="traffic_collision",
        severity=1,
        description="Multi-vehicle collision on Hwy 101.",
        status="DISPATCHED",
        latitude=37.7749,
        longitude=-122.4194,
        triage_summary="High severity rollover detected.",
        threat_assessment="Active fire hazard."
    )
    assert inc.id == inc_id
    assert inc.tracking_code == "TRK-8821"
    assert inc.severity == 1
    assert inc.latitude == 37.7749


def test_responder_unit_model_instantiation():
    """Tests ResponderUnit SQLAlchemy model instantiation."""
    unit_id = uuid.uuid4()
    unit = ResponderUnit(
        id=unit_id,
        call_sign="Medic 101",
        unit_type="ALS",
        status="AVAILABLE",
        current_lat=37.7700,
        current_lon=-122.4100
    )
    assert unit.id == unit_id
    assert unit.call_sign == "Medic 101"
    assert unit.status == "AVAILABLE"


def test_dispatch_assignment_model_instantiation():
    """Tests DispatchAssignment SQLAlchemy model instantiation."""
    disp_id = uuid.uuid4()
    inc_id = uuid.uuid4()
    unit_id = uuid.uuid4()

    dispatch = DispatchAssignment(
        id=disp_id,
        incident_id=inc_id,
        unit_id=unit_id,
        status="assigned"
    )
    assert dispatch.id == disp_id
    assert dispatch.incident_id == inc_id


def test_public_alert_model_instantiation():
    """Tests PublicAlert SQLAlchemy model instantiation."""
    alert_id = uuid.uuid4()
    alert = PublicAlert(
        id=alert_id,
        title="Emergency Warning",
        message="Traffic alert: Hwy 101 closed.",
        severity="CRITICAL"
    )
    assert alert.id == alert_id
    assert alert.severity == "CRITICAL"


def test_agent_audit_log_model_instantiation():
    """Tests AgentAuditLog SQLAlchemy model instantiation."""
    log_id = uuid.uuid4()
    audit_log = AgentAuditLog(
        id=log_id,
        agent_name="VisionAgent",
        action_taken="HAZARD_DETECTED"
    )
    assert audit_log.id == log_id
    assert audit_log.agent_name == "VisionAgent"


def test_incident_report_model_instantiation():
    """Tests IncidentReport SQLAlchemy model instantiation."""
    rep_id = uuid.uuid4()
    report = IncidentReport(
        id=rep_id,
        incident_id="INC-8821",
        tracking_code="TRK-8821",
        title="Emergency Audit: INC-8821",
        ai_summary="Multi-agent dispatch pipeline completed.",
        officer_notes="Supervisor verified all actions.",
        recommendations=["Signal preemption executed."],
        timeline_data=[{"time": "10:12:05", "event": "Incident received"}],
        evidence_images=[{"image_id": "IMG-001", "hazard": "Fire"}],
        metrics_data={"sla_compliance_score": 100}
    )
    assert report.id == rep_id
    assert report.incident_id == "INC-8821"
    assert report.metrics_data["sla_compliance_score"] == 100


def test_hospital_model_instantiation():
    """Tests Hospital SQLAlchemy model instantiation and emergency phone number."""
    h_id = uuid.uuid4()
    hosp = Hospital(
        id=h_id,
        code="HOSP-NGP-01",
        name="GMCH Nagpur",
        emergency_phone="7796119389",
        trauma_level="Level I",
        address="Medical Square, Nagpur",
        city="Nagpur",
        latitude=21.1367,
        longitude=79.0995,
        total_icu_beds=60,
        available_icu_beds=14
    )
    assert hosp.id == h_id
    assert hosp.emergency_phone == "7796119389"
    assert hosp.trauma_level == "Level I"
    assert hosp.city == "Nagpur"


def test_hospital_call_log_model_instantiation():
    """Tests HospitalCallLog SQLAlchemy model instantiation with target phone 7796119389."""
    call_id = uuid.uuid4()
    inc_id = uuid.uuid4()
    h_id = uuid.uuid4()
    call_log = HospitalCallLog(
        id=call_id,
        incident_id=inc_id,
        hospital_id=h_id,
        target_phone="7796119389",
        call_type="AUTOMATED_EMERGENCY_DISPATCH",
        status="CONNECTED",
        speech_transcript="Nagpur EOC Emergency Alert: Major accident near Wardha Road.",
        distance_km=2.1,
        eta_minutes=4.2,
        severity_level=1
    )
    assert call_log.id == call_id
    assert call_log.target_phone == "7796119389"
    assert call_log.status == "CONNECTED"
    assert call_log.distance_km == 2.1
