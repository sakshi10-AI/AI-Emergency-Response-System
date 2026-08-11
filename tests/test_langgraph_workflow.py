"""
Comprehensive Test Suite for LangGraph Emergency Response Multi-Agent Workflow

Tests:
1. Individual execution and fallbacks for all 12 agents
2. End-to-End workflow invocation
3. Parallel intake and parallel dispatch stages
4. Human approval node interrupts & approval flows
5. Recovery Agent failure recovery routing
"""

import pytest
import uuid
from agents.langgraph_schemas import (
    EmergencyResponseState,
    SupervisorInput, VisionInput, LocationInput, SeverityInput,
    HospitalInput, AmbulanceInput, TrafficInput, CommunicationInput,
    ReportInput, MemoryInput, LoggerInput, RecoveryInput
)
from agents.langgraph_agents import (
    supervisor_agent, vision_agent, location_agent, severity_agent,
    hospital_agent, ambulance_agent, traffic_agent, communication_agent,
    report_agent, memory_agent, logger_agent, recovery_agent
)
from agents.langgraph_workflow import (
    build_emergency_langgraph, run_emergency_workflow, emergency_response_graph
)


# ============================================================================
# 1. Test All 12 Agents Individually
# ============================================================================

def test_supervisor_agent():
    inp = SupervisorInput(incident_id="INC-1", description="Test", current_stage="INIT")
    out = supervisor_agent.fallback_execution(inp)
    assert out.next_node == "parallel_intake"
    assert out.routing_reason != ""

def test_vision_agent():
    inp = VisionInput(description="Vehicle collision with smoke", image_urls=["http://example.com/scene.jpg"])
    out = vision_agent.fallback_execution(inp)
    assert out.fire_or_smoke_detected is True
    assert len(out.detected_hazards) > 0

def test_location_agent():
    inp = LocationInput(latitude=37.7749, longitude=-122.4194, description="Central Plaza Crash")
    out = location_agent.fallback_execution(inp)
    assert out.latitude == 37.7749
    assert out.zone_type in ["URBAN", "SUBURBAN"]

def test_severity_agent():
    inp = SeverityInput(description="Critical multiple casualty incident with unconscious victims")
    out = severity_agent.fallback_execution(inp)
    assert out.severity_level == 1
    assert out.priority_category == "IMMEDIATE"
    assert out.life_threat_flag is True

def test_hospital_agent():
    inp = HospitalInput(latitude=37.7749, longitude=-122.4194, severity_level=1, patients_count=2)
    out = hospital_agent.fallback_execution(inp)
    assert out.primary_hospital.hospital_name != ""
    assert out.primary_hospital.available_icu_beds > 0

def test_ambulance_agent():
    inp = AmbulanceInput(latitude=37.7749, longitude=-122.4194, severity_level=1, required_units_count=2)
    out = ambulance_agent.fallback_execution(inp)
    assert out.total_units_dispatched == 2
    assert len(out.assigned_units) == 2

def test_traffic_agent():
    inp = TrafficInput(origin_lat=37.79, origin_lng=-122.40, destination_lat=37.77, destination_lng=-122.41, incident_type="CRASH")
    out = traffic_agent.fallback_execution(inp)
    assert out.congestion_level in ["CLEAR", "MODERATE", "HEAVY", "SEVERE"]
    assert len(out.optimal_route) > 0

def test_communication_agent():
    inp = CommunicationInput(incident_id="INC-1", summary="Car Crash", severity_level=1, location="Main St")
    out = communication_agent.fallback_execution(inp)
    assert "PRIORITY 1" in out.dispatcher_briefing or "Main St" in out.dispatcher_briefing
    assert out.public_sms_alert != ""

def test_report_agent():
    inp = ReportInput(incident_id="INC-1", tracking_code="EMG-100", description="Multi car collision")
    out = report_agent.fallback_execution(inp)
    assert out.tracking_code == "EMG-100"
    assert len(out.chronological_timeline) > 0

def test_memory_agent():
    inp = MemoryInput(action="RECALL", incident_id="INC-1", query_text="highway accident")
    out = memory_agent.fallback_execution(inp)
    assert out.status == "SUCCESS"
    assert len(out.similar_past_incidents) > 0

def test_logger_agent():
    inp = LoggerInput(node_name="test_node", incident_id="INC-1", event_type="INFO", message="Test log entry")
    out = logger_agent.fallback_execution(inp)
    assert out.persisted is True
    assert "test_node" in out.formatted_entry

def test_recovery_agent():
    inp = RecoveryInput(incident_id="INC-1", failed_node="severity_node", error_message="LLM API Timeout", partial_state={})
    out = recovery_agent.fallback_execution(inp)
    assert out.fallback_dispatch_triggered is True
    assert "severity_analysis" in out.repaired_state_updates


# ============================================================================
# 2. Test End-to-End LangGraph Execution
# ============================================================================

def test_end_to_end_workflow():
    incident_id = f"test-inc-{uuid.uuid4().hex[:6]}"
    final_state = run_emergency_workflow(
        incident_id=incident_id,
        description="Two car collision with moderate injuries on Highway 101",
        latitude=37.7749,
        longitude=-122.4194,
        address_text="Highway 101 Southbound Exit 4"
    )

    assert final_state.incident_id == incident_id
    assert final_state.status in ["COMPLETED", "RECOVERED"]
    assert final_state.vision_analysis != {}
    assert final_state.location_analysis != {}
    assert final_state.severity_analysis != {}
    assert final_state.hospital_recommendation != {}
    assert final_state.ambulance_assignment != {}
    assert final_state.traffic_analysis != {}
    assert final_state.communications != {}
    assert final_state.report != {}
    assert len(final_state.audit_logs) > 0


def test_critical_incident_human_approval():
    incident_id = f"critical-inc-{uuid.uuid4().hex[:6]}"
    
    # 1. Run without explicit approval (human_approval_granted=None) for Severity 1 incident
    state_pending = run_emergency_workflow(
        incident_id=incident_id,
        description="Critical fatal multi-vehicle pileup with unconscious victims and active fire",
        latitude=37.7749,
        longitude=-122.4194,
        human_approval_granted=None
    )
    
    assert state_pending.severity_analysis.get("severity_level") == 1
    assert state_pending.human_approval_required is True

    # 2. Run with explicit human approval (human_approval_granted=True)
    state_approved = run_emergency_workflow(
        incident_id=incident_id,
        description="Critical fatal multi-vehicle pileup with unconscious victims and active fire",
        latitude=37.7749,
        longitude=-122.4194,
        human_approval_granted=True
    )

    assert state_approved.status in ["COMPLETED", "RECOVERED"]
    assert state_approved.report != {}
