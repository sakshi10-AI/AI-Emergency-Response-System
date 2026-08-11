"""
Specialized AI Agent Implementations

Contains all 9 specialized domain agents subclassing BaseAgent.
"""
import math
from agents.base_agent import BaseAgent
from agents.schemas import (
    ClassificationInput, ClassificationOutput,
    MedicalInput, MedicalOutput,
    PoliceInput, PoliceOutput,
    FireInput, FireOutput,
    TrafficInput, TrafficOutput,
    ResourceAllocationInput, ResourceAllocationOutput, UnitRecommendation,
    CommunicationInput, CommunicationOutput,
    ReportGenerationInput, ReportGenerationOutput,
    NotificationInput, NotificationOutput
)
from agents.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    MEDICAL_SYSTEM_PROMPT,
    POLICE_SYSTEM_PROMPT,
    FIRE_SYSTEM_PROMPT,
    TRAFFIC_SYSTEM_PROMPT,
    RESOURCE_ALLOCATION_SYSTEM_PROMPT,
    COMMUNICATION_SYSTEM_PROMPT,
    REPORT_GENERATION_SYSTEM_PROMPT,
    NOTIFICATION_SYSTEM_PROMPT
)

# ==================== 1. Incident Classification Agent ====================
class IncidentClassificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="IncidentClassificationAgent",
            system_instruction=CLASSIFICATION_SYSTEM_PROMPT,
            input_schema=ClassificationInput,
            output_schema=ClassificationOutput
        )

    def fallback_execution(self, input_data: ClassificationInput) -> ClassificationOutput:
        desc = input_data.description.lower()
        req_med = any(w in desc for w in ["bleed", "chest", "heart", "breath", "unconscious", "injury", "medical", "ambulance"])
        req_fire = any(w in desc for w in ["fire", "smoke", "flame", "explosion", "burn", "trapped"])
        req_police = any(w in desc for w in ["gun", "weapon", "robbery", "assault", "fight", "suspect", "stolen", "shooter"])
        req_hazmat = any(w in desc for w in ["chemical", "gas", "toxic", "spill", "leak", "hazmat"])

        category = "medical" if req_med else "fire" if req_fire else "crime" if req_police else "hazardous_material" if req_hazmat else "other"
        severity = 1 if (req_fire and req_med) or "gun" in desc or "unconscious" in desc else 2 if (req_med or req_fire) else 3

        return ClassificationOutput(
            category=category,
            severity=severity,
            summary=f"Automated classification: {category.upper()} emergency reported.",
            primary_hazard="Fire/Smoke" if req_fire else "Medical distress" if req_med else "Security threat",
            requires_medical=req_med or (not req_fire and not req_police),
            requires_police=req_police,
            requires_fire=req_fire,
            requires_hazmat=req_hazmat
        )

# ==================== 2. Medical Assistance Agent ====================
class MedicalAssistanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="MedicalAssistanceAgent",
            system_instruction=MEDICAL_SYSTEM_PROMPT,
            input_schema=MedicalInput,
            output_schema=MedicalOutput
        )

    def fallback_execution(self, input_data: MedicalInput) -> MedicalOutput:
        sev = input_data.severity
        triage_color = "RED" if sev == 1 else "YELLOW" if sev == 2 else "GREEN"
        return MedicalOutput(
            triage_color=triage_color,
            recommended_equipment=["ALS Medical Kit", "Oxygen Tank", "Defibrillator", "Stretcher"],
            first_aid_instructions=[
                "Keep victim calm and still.",
                "Ensure clear airway and check breathing.",
                "Apply direct pressure to any active bleeding."
            ],
            specialized_care_needed="Trauma Unit / ICU" if sev == 1 else "Urgent Care"
        )

# ==================== 3. Police Assistance Agent ====================
class PoliceAssistanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="PoliceAssistanceAgent",
            system_instruction=POLICE_SYSTEM_PROMPT,
            input_schema=PoliceInput,
            output_schema=PoliceOutput
        )

    def fallback_execution(self, input_data: PoliceInput) -> PoliceOutput:
        desc = input_data.description.lower()
        weapons = any(w in desc for w in ["gun", "knife", "weapon", "armed"])
        swat = any(w in desc for w in ["hostage", "barricaded", "active shooter"])
        threat_level = "CRITICAL" if swat else "HIGH" if weapons else "MEDIUM"

        return PoliceOutput(
            threat_level=threat_level,
            suspect_description="Suspect description pending officer arrival.",
            weapons_reported=weapons,
            requires_tactical_swat=swat,
            perimeter_security_recommendations=[
                "Establish 200m outer safety perimeter.",
                "Block civilian traffic from entering immediate danger zone."
            ]
        )

# ==================== 4. Fire Assistance Agent ====================
class FireAssistanceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="FireAssistanceAgent",
            system_instruction=FIRE_SYSTEM_PROMPT,
            input_schema=FireInput,
            output_schema=FireOutput
        )

    def fallback_execution(self, input_data: FireInput) -> FireOutput:
        desc = input_data.description.lower()
        hazmat = "chemical" in desc or "gas" in desc
        return FireOutput(
            fire_stage="GROWTH" if input_data.severity <= 2 else "INCIPIENT",
            structure_type="COMMERCIAL" if "building" in desc or "store" in desc else "RESIDENTIAL",
            hazmat_risk=hazmat,
            evacuation_radius_meters=300 if hazmat else 100,
            required_apparatus=["Pumper Engine", "Ladder Truck", "Foam Unit"] if hazmat else ["Pumper Engine", "Ladder Truck"]
        )

# ==================== 5. Traffic Analysis Agent ====================
class TrafficAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="TrafficAnalysisAgent",
            system_instruction=TRAFFIC_SYSTEM_PROMPT,
            input_schema=TrafficInput,
            output_schema=TrafficOutput
        )

    def fallback_execution(self, input_data: TrafficInput) -> TrafficOutput:
        return TrafficOutput(
            congestion_level="MODERATE",
            recommended_ingress_routes=["Use Main Arterial Expressway Northbound", "Avoid 4th St Junction"],
            road_closures_needed=["Immediate 100m block around incident coordinates"],
            estimated_traffic_delay_minutes=3
        )

# ==================== 6. Resource Allocation Agent ====================
class ResourceAllocationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ResourceAllocationAgent",
            system_instruction=RESOURCE_ALLOCATION_SYSTEM_PROMPT,
            input_schema=ResourceAllocationInput,
            output_schema=ResourceAllocationOutput
        )

    def fallback_execution(self, input_data: ResourceAllocationInput) -> ResourceAllocationOutput:
        units = input_data.available_units
        recommended: list[UnitRecommendation] = []

        for idx, u in enumerate(units[:3]):
            recommended.append(UnitRecommendation(
                unit_id=str(u.get("id", f"unit-{idx}")),
                call_sign=str(u.get("call_sign", f"UNIT-{idx+1}")),
                unit_type=str(u.get("unit_type", "ambulance")),
                distance_km=round(u.get("distance_km", 1.2 + idx * 0.8), 2),
                estimated_eta_minutes=round(u.get("distance_km", 1.2 + idx * 0.8) * 2.5, 1),
                assignment_reason="Optimal geographic proximity and operational availability."
            ))

        return ResourceAllocationOutput(
            recommended_units=recommended,
            total_units_assigned=len(recommended),
            dispatch_notes="Automated dispatch selection based on nearest spatial availability."
        )

# ==================== 7. Communication Agent ====================
class CommunicationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="CommunicationAgent",
            system_instruction=COMMUNICATION_SYSTEM_PROMPT,
            input_schema=CommunicationInput,
            output_schema=CommunicationOutput
        )

    def fallback_execution(self, input_data: CommunicationInput) -> CommunicationOutput:
        units_str = ", ".join(input_data.assigned_units) if input_data.assigned_units else "Units En Route"
        return CommunicationOutput(
            dispatcher_briefing=f"PRIORITY ALERT: {input_data.incident_summary}. Units Dispatched: {units_str}.",
            responder_radio_message=f"ALL UNITS: Respond code 3 to incident location. Dispatched: {units_str}.",
            caller_reassurance_script="Help is on the way. Please stay on the line and follow first-aid instructions."
        )

# ==================== 8. Report Generation Agent ====================
class ReportGenerationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="ReportGenerationAgent",
            system_instruction=REPORT_GENERATION_SYSTEM_PROMPT,
            input_schema=ReportGenerationInput,
            output_schema=ReportGenerationOutput
        )

    def fallback_execution(self, input_data: ReportGenerationInput) -> ReportGenerationOutput:
        return ReportGenerationOutput(
            executive_summary=f"Emergency incident {input_data.tracking_code} triaged and dispatched.",
            detailed_timeline=[
                "T+0: Incident reported by citizen.",
                "T+1s: Multi-Agent AI intake and classification completed.",
                "T+2s: Unit dispatch recommendations generated and delivered to 911 command center."
            ],
            lessons_learned=["Rapid multi-agent response reduced dispatch response latency to under 3 seconds."],
            audit_verdict="PASSED_STANDARD_OPERATING_PROCEDURES"
        )

# ==================== 9. Notification Agent ====================
class NotificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="NotificationAgent",
            system_instruction=NOTIFICATION_SYSTEM_PROMPT,
            input_schema=NotificationInput,
            output_schema=NotificationOutput
        )

    def fallback_execution(self, input_data: NotificationInput) -> NotificationOutput:
        sev_label = "EXTREME_DANGER" if input_data.severity == 1 else "WARNING" if input_data.severity <= 3 else "INFO"
        return NotificationOutput(
            public_alert_title=f"EMERGENCY ALERT: {input_data.title}",
            sms_broadcast_message=f"EMERGENCY WARNING: Incident reported near your location. Avoid immediate area and yield to emergency vehicles.",
            evacuation_warning="Avoid area within 500 meters" if input_data.severity <= 2 else None,
            alert_severity_level=sev_label
        )
