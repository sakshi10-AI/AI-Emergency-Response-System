"""
AI Agents API Router

Exposes endpoints for triggering multi-agent AI emergency triage, dispatch analysis,
and audit logging.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from database.connection import get_db
from services.incident_service import incident_service
from services.unit_service import unit_service
from agents.orchestrator import coordinator_agent
from agents.schemas import OrchestratorPipelineInput, OrchestratorPipelineOutput
from models.agent_log import AgentAuditLog
from authentication.rbac import require_roles
from models.user import User
import json

router = APIRouter(prefix="/api/v1/dispatch", tags=["AI Multi-Agent Dispatch"])

@router.post("/{incident_id}/analyze", response_model=OrchestratorPipelineOutput, status_code=status.HTTP_200_OK, summary="Run Multi-Agent Triage & Dispatch Analysis")
async def analyze_incident_with_agents(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["dispatcher", "admin", "responder"]))
):
    """Triggers central Emergency Coordinator Agent to run 10-agent pipeline on an emergency incident."""
    # 1. Fetch incident record
    incident = await incident_service.get_by_id(db, incident_id)

    # 2. Fetch available responder units for spatial matching
    units = await unit_service.list_units(db, status="available")
    units_data = [
        {
            "id": str(u.id),
            "call_sign": u.call_sign,
            "unit_type": u.unit_type,
            "current_lat": u.current_lat,
            "current_lon": u.current_lon,
            "distance_km": round(math_dist(incident.latitude, incident.longitude, u.current_lat, u.current_lon), 2)
        }
        for u in units
    ]

    # 3. Construct orchestrator input
    pipe_input = OrchestratorPipelineInput(
        incident_id=incident.id,
        description=incident.description,
        latitude=incident.latitude,
        longitude=incident.longitude,
        address_text=incident.address_text
    )

    # 4. Execute Multi-Agent Pipeline
    result = await coordinator_agent.execute_pipeline(pipe_input, available_units=units_data)

    # 5. Persist agent assessment to incident record
    incident.category = result.classification.category
    incident.severity = result.classification.severity
    incident.triage_summary = result.classification.summary
    incident.status = "triaged"
    
    if result.fire_assessment:
        incident.threat_assessment = f"Fire Stage: {result.fire_assessment.fire_stage}, HazMat: {result.fire_assessment.hazmat_risk}"
    elif result.police_assessment:
        incident.threat_assessment = f"Threat Level: {result.police_assessment.threat_level}, Weapons: {result.police_assessment.weapons_reported}"
    elif result.medical_assessment:
        incident.threat_assessment = f"Medical Triage: {result.medical_assessment.triage_color}"

    # 6. Record Agent Audit Log (convert UUID/datetime objects via Pydantic model_dump_json)
    audit_log = AgentAuditLog(
        agent_name="EmergencyCoordinatorAgent",
        incident_id=incident.id,
        action_taken="MULTI_AGENT_PIPELINE_EXECUTED",
        input_payload=json.loads(pipe_input.model_dump_json()),
        output_response=json.loads(result.model_dump_json())
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(incident)

    return result

def math_dist(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance approximation in kilometers."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
