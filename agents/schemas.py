"""
AI Agent Pydantic Schemas (Input/Output Specifications)

Defines strongly-typed inputs and outputs for all 10 specialized emergency response agents.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID

# ==================== 1. Incident Classification Agent ====================
class ClassificationInput(BaseModel):
    description: str = Field(..., description="Caller description or transcript")
    latitude: float
    longitude: float
    address_text: Optional[str] = None

class ClassificationOutput(BaseModel):
    category: str = Field(..., description="medical, fire, crime, hazardous_material, traffic, natural_disaster, other")
    severity: int = Field(..., ge=1, le=5, description="1 (Critical/Life Threatening) to 5 (Minor)")
    summary: str = Field(..., description="Concise triage summary")
    primary_hazard: str
    requires_medical: bool = False
    requires_police: bool = False
    requires_fire: bool = False
    requires_hazmat: bool = False

# ==================== 2. Medical Assistance Agent ====================
class MedicalInput(BaseModel):
    description: str
    severity: int
    triage_notes: Optional[str] = None

class MedicalOutput(BaseModel):
    triage_color: str = Field(..., description="RED (Immediate), YELLOW (Delayed), GREEN (Minor), BLACK (Deceased)")
    recommended_equipment: List[str] = Field(default_factory=list, description="e.g., Defibrillator, ALS Kit, Stretcher")
    first_aid_instructions: List[str] = Field(default_factory=list, description="Caller emergency first-aid guidance")
    specialized_care_needed: Optional[str] = None

# ==================== 3. Police Assistance Agent ====================
class PoliceInput(BaseModel):
    description: str
    severity: int

class PoliceOutput(BaseModel):
    threat_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    suspect_description: Optional[str] = None
    weapons_reported: bool = False
    requires_tactical_swat: bool = False
    perimeter_security_recommendations: List[str] = Field(default_factory=list)

# ==================== 4. Fire Assistance Agent ====================
class FireInput(BaseModel):
    description: str
    severity: int

class FireOutput(BaseModel):
    fire_stage: str = Field(..., description="INCIPIENT, GROWTH, FULLY_DEVELOPED, DECAY, UNKNOWN")
    structure_type: str = Field(..., description="RESIDENTIAL, COMMERCIAL, INDUSTRIAL, WILDLAND, VEHICLE")
    hazmat_risk: bool = False
    evacuation_radius_meters: int = Field(default=100)
    required_apparatus: List[str] = Field(default_factory=list, description="Ladder Truck, Foam Tender, Engine")

# ==================== 5. Traffic Analysis Agent ====================
class TrafficInput(BaseModel):
    latitude: float
    longitude: float
    incident_type: str

class TrafficOutput(BaseModel):
    congestion_level: str = Field(..., description="CLEAR, MODERATE, HEAVY, SEVERE")
    recommended_ingress_routes: List[str] = Field(default_factory=list)
    road_closures_needed: List[str] = Field(default_factory=list)
    estimated_traffic_delay_minutes: int = Field(default=0)

# ==================== 6. Resource Allocation Agent ====================
class ResourceAllocationInput(BaseModel):
    incident_id: UUID
    category: str
    severity: int
    requires_medical: bool
    requires_police: bool
    requires_fire: bool
    requires_hazmat: bool
    available_units: List[Dict[str, Any]]

class UnitRecommendation(BaseModel):
    unit_id: str
    call_sign: str
    unit_type: str
    distance_km: float
    estimated_eta_minutes: float
    assignment_reason: str

class ResourceAllocationOutput(BaseModel):
    recommended_units: List[UnitRecommendation]
    total_units_assigned: int
    dispatch_notes: str

# ==================== 7. Communication Agent ====================
class CommunicationInput(BaseModel):
    incident_summary: str
    severity: int
    assigned_units: List[str]
    medical_instructions: List[str]

class CommunicationOutput(BaseModel):
    dispatcher_briefing: str = Field(..., description="High priority briefing for 911 dispatcher")
    responder_radio_message: str = Field(..., description="Tactical radio dispatch message")
    caller_reassurance_script: str = Field(..., description="Script for caller reassurance")

# ==================== 8. Report Generation Agent ====================
class ReportGenerationInput(BaseModel):
    incident_id: UUID
    tracking_code: str
    description: str
    classification: Dict[str, Any]
    assignments: List[Dict[str, Any]]

class ReportGenerationOutput(BaseModel):
    executive_summary: str
    detailed_timeline: List[str]
    lessons_learned: List[str]
    audit_verdict: str

# ==================== 9. Notification Agent ====================
class NotificationInput(BaseModel):
    title: str
    description: str
    severity: int
    latitude: float
    longitude: float
    target_radius_km: float

class NotificationOutput(BaseModel):
    public_alert_title: str
    sms_broadcast_message: str
    evacuation_warning: Optional[str] = None
    alert_severity_level: str = Field(..., description="INFO, WARNING, EXTREME_DANGER")

# ==================== 10. Central Orchestrator State ====================
class OrchestratorPipelineInput(BaseModel):
    incident_id: UUID
    description: str
    latitude: float
    longitude: float
    address_text: Optional[str] = None

class OrchestratorPipelineOutput(BaseModel):
    incident_id: UUID
    tracking_code: str
    classification: ClassificationOutput
    medical_assessment: Optional[MedicalOutput] = None
    police_assessment: Optional[PoliceOutput] = None
    fire_assessment: Optional[FireOutput] = None
    traffic_analysis: Optional[TrafficOutput] = None
    resource_allocation: ResourceAllocationOutput
    communications: CommunicationOutput
    notification: NotificationOutput
    incident_report: ReportGenerationOutput
    execution_duration_seconds: float
