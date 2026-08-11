"""
LangGraph Workflow State and Agent Pydantic Schemas

Defines the shared graph state and strongly-typed input/output specifications for
all 12 specialized emergency response agents.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID

# ============================================================================
# Shared Graph State Definition
# ============================================================================

class EmergencyResponseState(BaseModel):
    """
    Complete state graph context shared across all 12 agents in the LangGraph workflow.
    """
    incident_id: str = Field(default="", description="Unique incident identifier")
    tracking_code: str = Field(default="", description="Human-readable tracking code")
    description: str = Field(default="", description="Original incident description or transcript")
    latitude: float = Field(default=0.0, description="Latitude coordinate")
    longitude: float = Field(default=0.0, description="Longitude coordinate")
    address_text: Optional[str] = Field(default=None, description="Reported street address")
    image_urls: List[str] = Field(default_factory=list, description="Visual scene photo URLs")
    video_urls: List[str] = Field(default_factory=list, description="Visual scene video URLs")

    # Workflow Control Flags
    execution_stage: str = Field(default="INIT", description="Current execution stage")
    status: str = Field(default="INIT", description="Workflow status (INIT, ANALYZING, AWAITING_APPROVAL, DISPATCHING, COMPLETED, RECOVERED, FAILED)")
    human_approval_required: bool = Field(default=False, description="Flag indicating human supervisor approval is required")
    human_approval_granted: Optional[bool] = Field(default=None, description="True if approved, False if rejected")
    human_approval_notes: Optional[str] = Field(default=None, description="Notes from human supervisor")
    recovery_triggered: bool = Field(default=False, description="True if recovery node was activated")

    # Outputs from Specialized Agents
    supervisor_decision: Dict[str, Any] = Field(default_factory=dict, description="Output from Supervisor Agent")
    vision_analysis: Dict[str, Any] = Field(default_factory=dict, description="Output from Vision Agent")
    location_analysis: Dict[str, Any] = Field(default_factory=dict, description="Output from Location Agent")
    severity_analysis: Dict[str, Any] = Field(default_factory=dict, description="Output from Severity Agent")
    hospital_recommendation: Dict[str, Any] = Field(default_factory=dict, description="Output from Hospital Agent")
    ambulance_assignment: Dict[str, Any] = Field(default_factory=dict, description="Output from Ambulance Agent")
    traffic_analysis: Dict[str, Any] = Field(default_factory=dict, description="Output from Traffic Agent")
    communications: Dict[str, Any] = Field(default_factory=dict, description="Output from Communication Agent")
    report: Dict[str, Any] = Field(default_factory=dict, description="Output from Report Agent")
    recovery_details: Dict[str, Any] = Field(default_factory=dict, description="Output from Recovery Agent")

    # Accumulated Memory, Logs & Errors
    memory_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Memory recall and storage logs")
    audit_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Structured log trace")
    error_logs: List[Dict[str, Any]] = Field(default_factory=list, description="Caught error exceptions and diagnostics")


# ============================================================================
# Individual Agent Input & Output Schemas
# ============================================================================

# 1. Supervisor Agent
class SupervisorInput(BaseModel):
    incident_id: str
    description: str
    current_stage: str
    severity_score: Optional[int] = None
    has_errors: bool = False

class SupervisorOutput(BaseModel):
    next_node: str = Field(..., description="Target node identifier to route execution")
    routing_reason: str = Field(..., description="Rationale for routing decision")
    requires_human_approval: bool = Field(default=False)
    action_plan: List[str] = Field(default_factory=list)

# 2. Vision Agent
class VisionInput(BaseModel):
    description: str
    image_urls: List[str] = Field(default_factory=list)
    video_urls: List[str] = Field(default_factory=list)

class VisualHazard(BaseModel):
    hazard_type: str
    severity_level: str
    confidence: float
    location_in_scene: str

class VisionOutput(BaseModel):
    detected_hazards: List[VisualHazard] = Field(default_factory=list)
    victims_visible_count: int = Field(default=0)
    vehicles_involved_count: int = Field(default=0)
    fire_or_smoke_detected: bool = Field(default=False)
    structural_damage_detected: bool = Field(default=False)
    scene_summary: str = Field(..., description="Overall visual assessment summary")

# 3. Location Agent
class LocationInput(BaseModel):
    latitude: float
    longitude: float
    address_text: Optional[str] = None
    description: str

class LocationOutput(BaseModel):
    formatted_address: str
    latitude: float
    longitude: float
    nearest_landmark: str
    zone_type: str = Field(..., description="URBAN, SUBURBAN, RURAL, HIGHWAY, INDUSTRIAL")
    accessibility_restrictions: List[str] = Field(default_factory=list)
    geofence_flags: List[str] = Field(default_factory=list)

# 4. Severity Agent
class SeverityInput(BaseModel):
    description: str
    vision_assessment: Optional[Dict[str, Any]] = None
    location_assessment: Optional[Dict[str, Any]] = None

class SeverityOutput(BaseModel):
    severity_level: int = Field(..., ge=1, le=5, description="1 (Critical/Catastrophic) to 5 (Minor)")
    priority_category: str = Field(..., description="IMMEDIATE, URGENT, DELAYED, LOW_PRIORITY")
    risk_score: float = Field(..., ge=0.0, le=100.0)
    life_threat_flag: bool = Field(default=False)
    severity_rationale: str = Field(...)

# 5. Hospital Agent
class HospitalInput(BaseModel):
    latitude: float
    longitude: float
    severity_level: int
    required_specialties: List[str] = Field(default_factory=list)
    patients_count: int = Field(default=1)

class HospitalRecommendation(BaseModel):
    hospital_id: str
    hospital_name: str
    distance_km: float
    estimated_travel_minutes: float
    trauma_level: str
    available_icu_beds: int
    specialty_match: bool
    routing_reason: str

class HospitalOutput(BaseModel):
    primary_hospital: HospitalRecommendation
    backup_hospitals: List[HospitalRecommendation] = Field(default_factory=list)
    specialty_alert_sent: bool = Field(default=False)

# 6. Ambulance Agent
class AmbulanceInput(BaseModel):
    latitude: float
    longitude: float
    severity_level: int
    required_units_count: int = Field(default=1)
    special_equipment: List[str] = Field(default_factory=list)

class AssignedUnit(BaseModel):
    unit_id: str
    call_sign: str
    unit_type: str
    base_station: str
    distance_km: float
    eta_minutes: float
    equipment_installed: List[str] = Field(default_factory=list)

class AmbulanceOutput(BaseModel):
    assigned_units: List[AssignedUnit] = Field(default_factory=list)
    total_units_dispatched: int
    estimated_first_arrival_eta: float
    dispatch_notes: str

# 7. Traffic Agent
class TrafficInput(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    incident_type: str

class TrafficOutput(BaseModel):
    congestion_level: str = Field(..., description="CLEAR, MODERATE, HEAVY, SEVERE")
    optimal_route: List[str] = Field(default_factory=list)
    alternate_route: List[str] = Field(default_factory=list)
    estimated_delay_minutes: float = Field(default=0.0)
    traffic_signals_preempted: bool = Field(default=False)
    road_closures: List[str] = Field(default_factory=list)

# 8. Communication Agent
class CommunicationInput(BaseModel):
    incident_id: str
    summary: str
    severity_level: int
    location: str
    hospital_name: Optional[str] = None
    assigned_units: List[str] = Field(default_factory=list)

class CommunicationOutput(BaseModel):
    dispatcher_briefing: str
    tactical_radio_script: str
    public_sms_alert: str
    caller_reassurance_script: str
    hospital_notification_text: str

# 9. Report Agent
class ReportInput(BaseModel):
    incident_id: str
    tracking_code: str
    description: str
    severity: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    hospital: Optional[Dict[str, Any]] = None
    ambulance: Optional[Dict[str, Any]] = None
    traffic: Optional[Dict[str, Any]] = None
    communications: Optional[Dict[str, Any]] = None

class ReportOutput(BaseModel):
    incident_id: str
    tracking_code: str
    executive_summary: str
    chronological_timeline: List[str]
    performance_metrics: Dict[str, Any]
    compliance_audit: str
    lessons_learned: List[str]

# 10. Memory Agent
class MemoryInput(BaseModel):
    action: str = Field(..., description="STORE or RECALL")
    incident_id: str
    query_text: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None

class MemoryOutput(BaseModel):
    status: str
    similar_past_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    recalled_key_facts: List[str] = Field(default_factory=list)
    session_stored: bool = Field(default=False)

# 11. Logger Agent
class LoggerInput(BaseModel):
    node_name: str
    incident_id: str
    event_type: str = Field(..., description="INFO, WARNING, ERROR, STATE_CHANGE")
    message: str
    details: Optional[Dict[str, Any]] = None

class LoggerOutput(BaseModel):
    log_id: str
    timestamp: str
    persisted: bool
    formatted_entry: str

# 12. Recovery Agent
class RecoveryInput(BaseModel):
    incident_id: str
    failed_node: str
    error_message: str
    partial_state: Dict[str, Any]

class RecoveryOutput(BaseModel):
    recovery_status: str = Field(..., description="REPAIRED, FALLBACK_APPLIED, UNRECOVERABLE")
    repaired_state_updates: Dict[str, Any] = Field(default_factory=dict)
    corrective_actions_taken: List[str] = Field(default_factory=list)
    fallback_dispatch_triggered: bool = Field(default=False)
