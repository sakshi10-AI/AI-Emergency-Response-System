"""
Multi-Agent Architecture Integration & Verification Tests
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient

from agents.schemas import (
    ClassificationInput, MedicalInput, PoliceInput, FireInput, TrafficInput,
    ResourceAllocationInput, CommunicationInput, ReportGenerationInput, NotificationInput,
    OrchestratorPipelineInput
)
from agents.specialized_agents import (
    IncidentClassificationAgent, MedicalAssistanceAgent, PoliceAssistanceAgent,
    FireAssistanceAgent, TrafficAnalysisAgent, ResourceAllocationAgent,
    CommunicationAgent, ReportGenerationAgent, NotificationAgent
)
from agents.orchestrator import EmergencyCoordinatorAgent

@pytest.mark.asyncio
async def test_individual_specialized_agents():
    """Verify all 9 specialized domain agents execute and produce valid structured Pydantic outputs."""

    # 1. Classification Agent
    class_agent = IncidentClassificationAgent()
    class_out = await class_agent.execute(ClassificationInput(
        description="Structure fire on 3rd floor with heavy smoke and trapped residents",
        latitude=37.7749,
        longitude=-122.4194
    ))
    assert class_out.category in ["fire", "medical"]
    assert class_out.requires_fire is True

    # 2. Medical Agent
    med_agent = MedicalAssistanceAgent()
    med_out = await med_agent.execute(MedicalInput(description="Severe bleeding and chest pain", severity=1))
    assert med_out.triage_color in ["RED", "YELLOW", "GREEN"]
    assert len(med_out.first_aid_instructions) > 0

    # 3. Police Agent
    police_agent = PoliceAssistanceAgent()
    police_out = await police_agent.execute(PoliceInput(description="Armed robbery with handgun reported", severity=1))
    assert police_out.threat_level in ["HIGH", "CRITICAL"]
    assert police_out.weapons_reported is True

    # 4. Fire Agent
    fire_agent = FireAssistanceAgent()
    fire_out = await fire_agent.execute(FireInput(description="Chemical spill and toxic gas leak", severity=1))
    assert fire_out.hazmat_risk is True

    # 5. Traffic Agent
    traffic_agent = TrafficAnalysisAgent()
    traffic_out = await traffic_agent.execute(TrafficInput(latitude=37.7749, longitude=-122.4194, incident_type="fire"))
    assert traffic_out.congestion_level in ["CLEAR", "MODERATE", "HEAVY", "SEVERE"]

    # 6. Resource Allocation Agent
    res_agent = ResourceAllocationAgent()
    res_out = await res_agent.execute(ResourceAllocationInput(
        incident_id=uuid4(),
        category="fire",
        severity=1,
        requires_medical=True,
        requires_police=False,
        requires_fire=True,
        requires_hazmat=False,
        available_units=[{"id": "u1", "call_sign": "ENG-4", "unit_type": "fire_truck", "distance_km": 1.5}]
    ))
    assert res_out.total_units_assigned >= 1

    # 7. Communication Agent
    comm_agent = CommunicationAgent()
    comm_out = await comm_agent.execute(CommunicationInput(
        incident_summary="Structure Fire",
        severity=1,
        assigned_units=["ENG-4", "MEDIC-1"],
        medical_instructions=["Stay calm"]
    ))
    assert "ENG-4" in comm_out.dispatcher_briefing

    # 8. Report Generation Agent
    rep_agent = ReportGenerationAgent()
    rep_out = await rep_agent.execute(ReportGenerationInput(
        incident_id=uuid4(),
        tracking_code="EMG-TEST-101",
        description="Test description",
        classification={"category": "fire"},
        assignments=[]
    ))
    assert rep_out.audit_verdict == "PASSED_STANDARD_OPERATING_PROCEDURES"

    # 9. Notification Agent
    notif_agent = NotificationAgent()
    notif_out = await notif_agent.execute(NotificationInput(
        title="Fire Alert",
        description="Evacuate building",
        severity=1,
        latitude=37.7749,
        longitude=-122.4194,
        target_radius_km=2.0
    ))
    assert "EMERGENCY" in notif_out.public_alert_title

@pytest.mark.asyncio
async def test_orchestrator_pipeline_execution():
    """Verify central EmergencyCoordinatorAgent orchestrates the entire multi-agent workflow."""
    orchestrator = EmergencyCoordinatorAgent()
    pipeline_input = OrchestratorPipelineInput(
        incident_id=uuid4(),
        description="Major highway collision involving tanker truck leak and multiple injured victims",
        latitude=37.7749,
        longitude=-122.4194,
        address_text="Highway 101 KM 42"
    )
    units = [
        {"id": str(uuid4()), "call_sign": "AMB-101", "unit_type": "ambulance", "distance_km": 1.2},
        {"id": str(uuid4()), "call_sign": "HAZMAT-1", "unit_type": "hazmat_unit", "distance_km": 2.5}
    ]

    result = await orchestrator.execute_pipeline(pipeline_input, available_units=units)

    assert result.incident_id == pipeline_input.incident_id
    assert result.classification.requires_medical is True
    assert result.resource_allocation.total_units_assigned >= 1
    assert result.execution_duration_seconds > 0.0

@pytest.mark.asyncio
async def test_multi_agent_api_endpoint(client: AsyncClient):
    """Test POST /api/v1/dispatch/{incident_id}/analyze REST API endpoint."""
    # 1. Report incident
    report_res = await client.post("/api/v1/incidents/", json={
        "description": "Explosion and chemical leak reported at industrial warehouse",
        "latitude": 37.7749,
        "longitude": -122.4194
    })
    incident_id = report_res.json()["id"]

    # 2. Register dispatcher & login
    await client.post("/api/v1/auth/register", json={
        "email": "chiefdispatcher@emergency.gov",
        "full_name": "Chief Dispatcher Mark",
        "password": "Password123!",
        "role": "dispatcher"
    })
    login_res = await client.post("/api/v1/auth/login", data={
        "username": "chiefdispatcher@emergency.gov",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Trigger multi-agent analysis endpoint
    analyze_res = await client.post(f"/api/v1/dispatch/{incident_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200
    res_data = analyze_res.json()
    assert res_data["classification"]["category"] in ["hazardous_material", "fire", "medical"]
    assert "communications" in res_data
