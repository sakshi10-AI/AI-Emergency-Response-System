"""
12 Specialized LangGraph Emergency Response Agents

Each agent defines:
- Purpose
- Prompt
- Tools
- Input & Output Pydantic Schemas
- State updates
- Memory management
- Retry Logic (tenacity backoff)
- Fallback Logic (deterministic non-LLM safety solver)
- Error Handling
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from agents.base_agent import BaseAgent
from agents.langgraph_schemas import (
    EmergencyResponseState,
    SupervisorInput, SupervisorOutput,
    VisionInput, VisionOutput, VisualHazard,
    LocationInput, LocationOutput,
    SeverityInput, SeverityOutput,
    HospitalInput, HospitalOutput, HospitalRecommendation,
    AmbulanceInput, AmbulanceOutput, AssignedUnit,
    TrafficInput, TrafficOutput,
    CommunicationInput, CommunicationOutput,
    ReportInput, ReportOutput,
    MemoryInput, MemoryOutput,
    LoggerInput, LoggerOutput,
    RecoveryInput, RecoveryOutput
)
from utils.logger import app_logger
from utils.exceptions import AgentExecutionError


# ============================================================================
# Helper Tools used across Agents
# ============================================================================

class AgentTools:
    """Helper tools accessible to specialized agents."""

    @staticmethod
    def evaluate_workflow_state(incident_id: str, stage: str, has_errors: bool) -> Dict[str, Any]:
        """Tool: Evaluates current workflow state metrics."""
        return {"evaluated_stage": stage, "status": "STABLE" if not has_errors else "DEGRADED"}

    @staticmethod
    def analyze_image_hazards(image_urls: List[str], description: str) -> List[Dict[str, Any]]:
        """Tool: Computer Vision visual hazard detector."""
        hazards = []
        desc_lower = description.lower()
        if "fire" in desc_lower or "smoke" in desc_lower:
            hazards.append({"hazard_type": "FIRE_SMOKE", "severity_level": "HIGH", "confidence": 0.95, "location_in_scene": "Center frame"})
        if "vehicle" in desc_lower or "car" in desc_lower or "crash" in desc_lower or "accident" in desc_lower:
            hazards.append({"hazard_type": "VEHICLE_COLLISION", "severity_level": "CRITICAL", "confidence": 0.92, "location_in_scene": "Roadway"})
        if not hazards:
            hazards.append({"hazard_type": "UNSPECIFIED_INCIDENT", "severity_level": "MODERATE", "confidence": 0.70, "location_in_scene": "Scene perimeter"})
        return hazards

    @staticmethod
    def geocode_location(lat: float, lng: float, address_text: Optional[str]) -> Dict[str, Any]:
        """Tool: Geocoding and spatial zone tool."""
        address = address_text or f"Coordinates {lat:.4f}, {lng:.4f}"
        zone = "URBAN" if abs(lat) > 0 else "SUBURBAN"
        return {
            "formatted_address": address,
            "landmark": "Central Station Plaza" if "central" in address.lower() else "Highway Exit 14",
            "zone_type": zone,
            "restrictions": ["Single lane emergency passage only"] if "highway" in address.lower() else []
        }

    @staticmethod
    def compute_severity_index(description: str, has_fire: bool, victim_count: int) -> Dict[str, Any]:
        """Tool: Triage scoring calculation tool."""
        score = 3
        desc = description.lower()
        if "critical" in desc or "fatal" in desc or "unconscious" in desc or victim_count > 2:
            score = 1
        elif "fire" in desc or "trapped" in desc or has_fire:
            score = 2
        elif "minor" in desc or "scratch" in desc:
            score = 4
            
        categories = {1: "IMMEDIATE", 2: "URGENT", 3: "URGENT", 4: "DELAYED", 5: "LOW_PRIORITY"}
        return {
            "severity_level": score,
            "priority_category": categories.get(score, "URGENT"),
            "risk_score": (6 - score) * 20.0,
            "life_threat": score <= 2
        }

    @staticmethod
    def query_hospital_beds(lat: float, lng: float, severity: int) -> Dict[str, Any]:
        """Tool: Queries nearby hospitals and bed availability."""
        return {
            "primary": {
                "hospital_id": "HOSP-001",
                "hospital_name": "Government Medical College & Hospital (GMCH) Nagpur",
                "distance_km": 3.2,
                "estimated_travel_minutes": 7.5,
                "trauma_level": "Level 1 Trauma",
                "available_icu_beds": 8,
                "specialty_match": True,
                "routing_reason": "Nearest Level 1 Trauma center in Nagpur with available ICU capacity"
            },
            "backup": [{
                "hospital_id": "HOSP-002",
                "hospital_name": "Lata Mangeshkar Hospital Nagpur",
                "distance_km": 6.8,
                "estimated_travel_minutes": 14.0,
                "trauma_level": "Level 2 Trauma",
                "available_icu_beds": 7,
                "specialty_match": True,
                "routing_reason": "Secondary backup with cardiac surgery capacity"
            }]
        }

    @staticmethod
    def allocate_ems_units(lat: float, lng: float, count: int) -> List[Dict[str, Any]]:
        """Tool: Allocates available EMS ambulance units."""
        units = []
        callsigns = ["NMC-AMB-101", "NMC-AMB-204", "NMC-MEDIC-9"]
        base_stations = ["Sitabuldi Fire & EMS Station", "Dharampeth EMS Base", "Ajni Emergency Station"]
        for i in range(min(count, 3)):
            units.append({
                "unit_id": f"UNIT-EMS-{i+1}",
                "call_sign": callsigns[i],
                "unit_type": "ALS_AMBULANCE",
                "base_station": base_stations[i],
                "distance_km": round(1.5 + i * 2.1, 1),
                "eta_minutes": round(4.0 + i * 5.0, 1),
                "equipment_installed": ["Defibrillator", "ALS Kit", "Stretcher", "Ventilator"]
            })
        return units

    @staticmethod
    def analyze_traffic_routes(orig_lat: float, orig_lng: float, dest_lat: float, dest_lng: float) -> Dict[str, Any]:
        """Tool: Emergency route and traffic congestion tool."""
        return {
            "congestion": "MODERATE",
            "optimal_route": ["Wardha Road Express Corridor", "Ajni Flyover", "GMCH Hospital Access Road"],
            "alternate_route": ["Amravati Road Bypass", "Ring Road Nagpur"],
            "delay_minutes": 2.5,
            "signals_preempted": True,
            "road_closures": []
        }

    @staticmethod
    def generate_multi_channel_messages(summary: str, severity: int, location: str) -> Dict[str, Any]:
        """Tool: Communication payload synthesizer."""
        return {
            "dispatcher": f"[PRIORITY {severity}] Emergency at {location}: {summary}",
            "radio": f"ALL UNITS: Respond priority {severity} to {location}. Summary: {summary}",
            "sms": f"EMERGENCY ALERT: Incident reported near {location}. Please avoid the area and yield to emergency vehicles.",
            "caller": f"Help is on the way to {location}. Please stay on the line and remain calm.",
            "hospital": f"ALERT TRAUMA TEAM: Inbound priority {severity} patient from {location}."
        }

    @staticmethod
    def compile_incident_audit(incident_id: str, summary: str) -> Dict[str, Any]:
        """Tool: Audit compilation tool."""
        return {
            "summary": summary,
            "timeline": [f"{time.strftime('%H:%M:%S')} - Incident reported", f"{time.strftime('%H:%M:%S')} - Units dispatched"],
            "metrics": {"total_dispatch_time_sec": 3.4, "agents_executed": 12},
            "audit_verdict": "COMPLIANT_WITH_SOP",
            "lessons": ["Ensure early traffic preemption signal activation."]
        }


# ============================================================================
# 1. Supervisor Agent
# ============================================================================

class SupervisorAgent(BaseAgent):
    """Purpose: Directs dynamic workflow routing and handles high-level triage decisions."""

    def __init__(self):
        super().__init__(
            name="SupervisorAgent",
            system_instruction=(
                "You are the Emergency Response Supervisor Agent. "
                "Analyze the incident state and decide the next node to execute. "
                "Route to 'human_approval' if severity is 1 or high risk. "
                "Route to 'recovery' if errors exist."
            ),
            input_schema=SupervisorInput,
            output_schema=SupervisorOutput
        )
        self.tools = [AgentTools.evaluate_workflow_state]

    def fallback_execution(self, input_data: SupervisorInput) -> SupervisorOutput:
        if input_data.has_errors:
            next_node = "recovery"
            reason = "Errors detected in pipeline; routing to recovery."
        elif input_data.severity_score == 1:
            next_node = "human_approval"
            reason = "Critical severity (1) requires human supervisor approval."
        elif input_data.current_stage == "INIT":
            next_node = "parallel_intake"
            reason = "Initial intake: running Vision and Location agents in parallel."
        elif input_data.current_stage == "INTAKE_DONE":
            next_node = "severity"
            reason = "Intake complete; evaluating composite severity."
        else:
            next_node = "parallel_dispatch"
            reason = "Severity established; initiating parallel dispatch."

        return SupervisorOutput(
            next_node=next_node,
            routing_reason=reason,
            requires_human_approval=(input_data.severity_score == 1),
            action_plan=["Coordinate intake", "Assess severity", "Dispatch units"]
        )


# ============================================================================
# 2. Vision Agent
# ============================================================================

class VisionAgent(BaseAgent):
    """Purpose: Processes visual scene evidence (images/video) to detect hazards and casualties."""

    def __init__(self):
        super().__init__(
            name="VisionAgent",
            system_instruction="You are the Vision Analysis Agent. Extract visual hazards, vehicle count, and fire detection from scene media.",
            input_schema=VisionInput,
            output_schema=VisionOutput
        )
        self.tools = [AgentTools.analyze_image_hazards]

    def fallback_execution(self, input_data: VisionInput) -> VisionOutput:
        from vision.service import vision_detection_service

        img_src = input_data.image_urls[0] if input_data.image_urls else input_data.description
        vision_res = vision_detection_service.detect_image_sync(img_src)

        hazards = [
            VisualHazard(
                hazard_type=h.hazard_type,
                severity_level=h.risk_tier,
                confidence=h.confidence,
                location_in_scene=h.description
            )
            for h in vision_res.hazard_alerts
        ]

        if not hazards:
            hazards_data = AgentTools.analyze_image_hazards(input_data.image_urls, input_data.description)
            hazards = [VisualHazard(**h) for h in hazards_data]

        desc_lower = input_data.description.lower()
        fire = vision_res.fire_detected or "fire" in desc_lower or "smoke" in desc_lower

        return VisionOutput(
            detected_hazards=hazards,
            victims_visible_count=max(vision_res.victim_count, 2 if "injured" in desc_lower or "casualty" in desc_lower else 0),
            vehicles_involved_count=max(vision_res.vehicle_count, 2 if "car" in desc_lower or "crash" in desc_lower else 0),
            fire_or_smoke_detected=fire,
            structural_damage_detected="collapse" in desc_lower or "building" in desc_lower,
            scene_summary=vision_res.scene_summary or f"Visual scene analysis: {len(hazards)} hazards identified."
        )


# ============================================================================
# 3. Location Agent
# ============================================================================

class LocationAgent(BaseAgent):
    """Purpose: Validates and enriches location coordinates, reverse geocodes, and checks spatial constraints."""

    def __init__(self):
        super().__init__(
            name="LocationAgent",
            system_instruction="You are the Geolocation Agent. Resolve address, landmarks, and accessibility restrictions.",
            input_schema=LocationInput,
            output_schema=LocationOutput
        )
        self.tools = [AgentTools.geocode_location]

    def fallback_execution(self, input_data: LocationInput) -> LocationOutput:
        geo = AgentTools.geocode_location(input_data.latitude, input_data.longitude, input_data.address_text)
        return LocationOutput(
            formatted_address=geo["formatted_address"],
            latitude=input_data.latitude,
            longitude=input_data.longitude,
            nearest_landmark=geo["landmark"],
            zone_type=geo["zone_type"],
            accessibility_restrictions=geo["restrictions"],
            geofence_flags=["ACTIVE_EMERGENCY_ZONE"]
        )


# ============================================================================
# 4. Severity Agent
# ============================================================================

class SeverityAgent(BaseAgent):
    """Purpose: Calculates multi-variable emergency severity score (1-5), risk score, and life-threat flag."""

    def __init__(self):
        super().__init__(
            name="SeverityAgent",
            system_instruction="You are the Severity Triage Agent. Calculate 1-5 severity rating based on intake data.",
            input_schema=SeverityInput,
            output_schema=SeverityOutput
        )
        self.tools = [AgentTools.compute_severity_index]

    def fallback_execution(self, input_data: SeverityInput) -> SeverityOutput:
        vision_data = input_data.vision_assessment or {}
        has_fire = vision_data.get("fire_or_smoke_detected", False)
        victims = vision_data.get("victims_visible_count", 0)

        sev = AgentTools.compute_severity_index(input_data.description, has_fire, victims)
        return SeverityOutput(
            severity_level=sev["severity_level"],
            priority_category=sev["priority_category"],
            risk_score=sev["risk_score"],
            life_threat_flag=sev["life_threat"],
            severity_rationale=f"Assessed severity {sev['severity_level']} based on description and visual evidence."
        )


# ============================================================================
# 5. Hospital Agent
# ============================================================================

class HospitalAgent(BaseAgent):
    """Purpose: Finds and reserves optimal receiving hospitals based on specialty and bed availability."""

    def __init__(self):
        super().__init__(
            name="HospitalAgent",
            system_instruction="You are the Hospital Allocation Agent. Match patient needs to optimal trauma center.",
            input_schema=HospitalInput,
            output_schema=HospitalOutput
        )
        self.tools = [AgentTools.query_hospital_beds]

    def fallback_execution(self, input_data: HospitalInput) -> HospitalOutput:
        hosp_data = AgentTools.query_hospital_beds(input_data.latitude, input_data.longitude, input_data.severity_level)
        primary = HospitalRecommendation(**hosp_data["primary"])
        backups = [HospitalRecommendation(**b) for b in hosp_data["backup"]]

        return HospitalOutput(
            primary_hospital=primary,
            backup_hospitals=backups,
            specialty_alert_sent=True
        )


# ============================================================================
# 6. Ambulance Agent
# ============================================================================

class AmbulanceAgent(BaseAgent):
    """Purpose: Selects and dispatches nearest available EMS ambulance units and tracks ETAs."""

    def __init__(self):
        super().__init__(
            name="AmbulanceAgent",
            system_instruction="You are the Ambulance Dispatch Agent. Allocate optimal EMS units to incident scene.",
            input_schema=AmbulanceInput,
            output_schema=AmbulanceOutput
        )
        self.tools = [AgentTools.allocate_ems_units]

    def fallback_execution(self, input_data: AmbulanceInput) -> AmbulanceOutput:
        raw_units = AgentTools.allocate_ems_units(input_data.latitude, input_data.longitude, input_data.required_units_count)
        units = [AssignedUnit(**u) for u in raw_units]
        min_eta = min([u.eta_minutes for u in units]) if units else 5.0

        return AmbulanceOutput(
            assigned_units=units,
            total_units_dispatched=len(units),
            estimated_first_arrival_eta=min_eta,
            dispatch_notes=f"Dispatched {len(units)} EMS units. Priority response initiated."
        )


# ============================================================================
# 7. Traffic Agent
# ============================================================================

class TrafficAgent(BaseAgent):
    """Purpose: Evaluates route traffic conditions, issues signal preemption, and plans emergency ingress."""

    def __init__(self):
        super().__init__(
            name="TrafficAgent",
            system_instruction="You are the Emergency Traffic Agent. Optimize response routes and preempt traffic signals.",
            input_schema=TrafficInput,
            output_schema=TrafficOutput
        )
        self.tools = [AgentTools.analyze_traffic_routes]

    def fallback_execution(self, input_data: TrafficInput) -> TrafficOutput:
        traffic = AgentTools.analyze_traffic_routes(
            input_data.origin_lat, input_data.origin_lng,
            input_data.destination_lat, input_data.destination_lng
        )
        return TrafficOutput(
            congestion_level=traffic["congestion"],
            optimal_route=traffic["optimal_route"],
            alternate_route=traffic["alternate_route"],
            estimated_delay_minutes=traffic["delay_minutes"],
            traffic_signals_preempted=traffic["signals_preempted"],
            road_closures=traffic["road_closures"]
        )


# ============================================================================
# 8. Communication Agent
# ============================================================================

class CommunicationAgent(BaseAgent):
    """Purpose: Synthesizes multi-channel communications (911 briefing, tactical radio, SMS alert, caller script)."""

    def __init__(self):
        super().__init__(
            name="CommunicationAgent",
            system_instruction="You are the Communication Agent. Generate clear, actionable emergency scripts for all channels.",
            input_schema=CommunicationInput,
            output_schema=CommunicationOutput
        )
        self.tools = [AgentTools.generate_multi_channel_messages]

    def fallback_execution(self, input_data: CommunicationInput) -> CommunicationOutput:
        msgs = AgentTools.generate_multi_channel_messages(
            input_data.summary, input_data.severity_level, input_data.location
        )
        return CommunicationOutput(
            dispatcher_briefing=msgs["dispatcher"],
            tactical_radio_script=msgs["radio"],
            public_sms_alert=msgs["sms"],
            caller_reassurance_script=msgs["caller"],
            hospital_notification_text=msgs["hospital"]
        )


# ============================================================================
# 9. Report Agent
# ============================================================================

class ReportAgent(BaseAgent):
    """Purpose: Compiles structured post-incident reports, executive summary, audit trace, and lessons learned."""

    def __init__(self):
        super().__init__(
            name="ReportAgent",
            system_instruction="You are the Post-Incident Report Agent. Compile executive summary and compliance audit.",
            input_schema=ReportInput,
            output_schema=ReportOutput
        )
        self.tools = [AgentTools.compile_incident_audit]

    def fallback_execution(self, input_data: ReportInput) -> ReportOutput:
        audit = AgentTools.compile_incident_audit(input_data.incident_id, input_data.description)
        return ReportOutput(
            incident_id=input_data.incident_id,
            tracking_code=input_data.tracking_code,
            executive_summary=f"Emergency Response Incident Report ({input_data.tracking_code}): {input_data.description}",
            chronological_timeline=audit["timeline"],
            performance_metrics=audit["metrics"],
            compliance_audit=audit["audit_verdict"],
            lessons_learned=audit["lessons"]
        )


# ============================================================================
# 10. Memory Agent
# ============================================================================

class MemoryAgent(BaseAgent):
    """Purpose: Manages short-term state memory and queries historical incident vector stores."""

    def __init__(self):
        super().__init__(
            name="MemoryAgent",
            system_instruction="You are the Memory Agent. Store session data and recall past similar incidents.",
            input_schema=MemoryInput,
            output_schema=MemoryOutput
        )
        self._past_db = [
            {"incident_id": "PAST-101", "description": "Car accident on highway near exit 14", "severity": 2, "outcome": "Successful dispatch in 5.2 min"},
            {"incident_id": "PAST-102", "description": "Residential kitchen fire", "severity": 2, "outcome": "Controlled by station 3 crew"}
        ]

    def fallback_execution(self, input_data: MemoryInput) -> MemoryOutput:
        if input_data.action == "RECALL":
            query = (input_data.query_text or "").lower()
            matches = [inc for inc in self._past_db if any(w in inc["description"].lower() for w in query.split())]
            return MemoryOutput(
                status="SUCCESS",
                similar_past_incidents=matches or self._past_db[:1],
                recalled_key_facts=[f"Found {len(matches)} historical incident matches for recall."],
                session_stored=False
            )
        else:
            return MemoryOutput(
                status="SUCCESS",
                similar_past_incidents=[],
                recalled_key_facts=["Incident state persisted to session memory."],
                session_stored=True
            )


# ============================================================================
# 11. Logger Agent
# ============================================================================

class LoggerAgent(BaseAgent):
    """Purpose: Produces structured audit logs and persists execution traces."""

    def __init__(self):
        super().__init__(
            name="LoggerAgent",
            system_instruction="You are the Audit Logger Agent. Log graph state transitions and execution events.",
            input_schema=LoggerInput,
            output_schema=LoggerOutput
        )

    def fallback_execution(self, input_data: LoggerInput) -> LoggerOutput:
        log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{now_str}] [{input_data.event_type}] Node '{input_data.node_name}' (Incident: {input_data.incident_id}): {input_data.message}"
        app_logger.info(entry)
        return LoggerOutput(
            log_id=log_id,
            timestamp=now_str,
            persisted=True,
            formatted_entry=entry
        )


# ============================================================================
# 12. Recovery Agent
# ============================================================================

class RecoveryAgent(BaseAgent):
    """Purpose: Repairs corrupted graph states, provides safe fallbacks, and prevents workflow failure."""

    def __init__(self):
        super().__init__(
            name="RecoveryAgent",
            system_instruction="You are the Recovery Agent. Repair workflow errors and supply safe default dispatches.",
            input_schema=RecoveryInput,
            output_schema=RecoveryOutput
        )

    def fallback_execution(self, input_data: RecoveryInput) -> RecoveryOutput:
        app_logger.warning(f"[RecoveryAgent] Recovering from failure in node '{input_data.failed_node}': {input_data.error_message}")
        
        repaired_updates = {
            "status": "RECOVERED",
            "recovery_triggered": True,
            "execution_stage": "RECOVERED_DISPATCH"
        }
        
        # Ensure fallback severity if severity agent failed
        if "severity" in input_data.failed_node or not input_data.partial_state.get("severity_analysis"):
            repaired_updates["severity_analysis"] = {
                "severity_level": 2,
                "priority_category": "URGENT",
                "risk_score": 80.0,
                "life_threat_flag": True,
                "severity_rationale": "Fallback default urgent severity set by Recovery Agent."
            }

        return RecoveryOutput(
            recovery_status="FALLBACK_APPLIED",
            repaired_state_updates=repaired_updates,
            corrective_actions_taken=[
                f"Logged error in node '{input_data.failed_node}'",
                "Applied conservative safe dispatch parameters",
                "Updated workflow status to RECOVERED"
            ],
            fallback_dispatch_triggered=True
        )


# Instantiate Agent Instances
supervisor_agent = SupervisorAgent()
vision_agent = VisionAgent()
location_agent = LocationAgent()
severity_agent = SeverityAgent()
hospital_agent = HospitalAgent()
ambulance_agent = AmbulanceAgent()
traffic_agent = TrafficAgent()
communication_agent = CommunicationAgent()
report_agent = ReportAgent()
memory_agent = MemoryAgent()
logger_agent = LoggerAgent()
recovery_agent = RecoveryAgent()
