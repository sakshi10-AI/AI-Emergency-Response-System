"""
Complete LangGraph Emergency Response Workflow Architecture

Implements StateGraph with 12 specialized agents, parallel execution stages,
conditional branching, human approval interrupt nodes, failure recovery routing,
and state checkpointer memory.
"""

from typing import Dict, Any, List, Optional
import time
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

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
from utils.logger import app_logger


# ============================================================================
# Graph Node Functions
# ============================================================================

def logger_start_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Logger Agent initialization log."""
    res = logger_agent.execute_sync(LoggerInput(
        node_name="logger_start",
        incident_id=state.incident_id,
        event_type="INFO",
        message="Workflow execution started."
    ))
    return {
        "execution_stage": "INIT",
        "status": "ANALYZING",
        "audit_logs": state.audit_logs + [res.model_dump()]
    }


def memory_fetch_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Memory Agent context recall."""
    res = memory_agent.execute_sync(MemoryInput(
        action="RECALL",
        incident_id=state.incident_id,
        query_text=state.description
    ))
    return {
        "memory_logs": state.memory_logs + [res.model_dump()]
    }


def vision_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Vision Agent visual assessment (Stage 1 Parallel)."""
    try:
        res = vision_agent.execute_sync(VisionInput(
            description=state.description,
            image_urls=state.image_urls,
            video_urls=state.video_urls
        ))
        return {"vision_analysis": res.model_dump()}
    except Exception as e:
        app_logger.error(f"[vision_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "vision_node", "error": str(e)}]
        }


def location_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Location Agent geocoding (Stage 1 Parallel)."""
    try:
        res = location_agent.execute_sync(LocationInput(
            latitude=state.latitude,
            longitude=state.longitude,
            address_text=state.address_text,
            description=state.description
        ))
        return {"location_analysis": res.model_dump()}
    except Exception as e:
        app_logger.error(f"[location_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "location_node", "error": str(e)}]
        }


def severity_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Severity Agent composite triage calculation."""
    try:
        res = severity_agent.execute_sync(SeverityInput(
            description=state.description,
            vision_assessment=state.vision_analysis,
            location_assessment=state.location_analysis
        ))
        return {
            "severity_analysis": res.model_dump(),
            "execution_stage": "INTAKE_COMPLETED"
        }
    except Exception as e:
        app_logger.error(f"[severity_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "severity_node", "error": str(e)}]
        }


def supervisor_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Supervisor Agent evaluation and routing decision."""
    try:
        sev_level = state.severity_analysis.get("severity_level") if state.severity_analysis else None
        has_errors = len(state.error_logs) > 0
        
        res = supervisor_agent.execute_sync(SupervisorInput(
            incident_id=state.incident_id,
            description=state.description,
            current_stage=state.execution_stage,
            severity_score=sev_level,
            has_errors=has_errors
        ))
        
        return {
            "supervisor_decision": res.model_dump(),
            "human_approval_required": res.requires_human_approval
        }
    except Exception as e:
        app_logger.error(f"[supervisor_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "supervisor_node", "error": str(e)}]
        }


def human_approval_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """
    Node: Human Approval Checkpoint for critical Severity-1 incidents.
    If approval is pending, sets status to AWAITING_APPROVAL.
    If granted, proceeds to dispatch. If rejected, triggers recovery.
    """
    if state.human_approval_granted is None:
        app_logger.info(f"[human_approval_node] Incident {state.incident_id} requires human supervisor verification.")
        return {
            "status": "AWAITING_APPROVAL",
            "human_approval_notes": "Pending dispatcher sign-off for Severity-1 dispatch."
        }
    elif state.human_approval_granted is True:
        app_logger.info(f"[human_approval_node] Incident {state.incident_id} APPROVED by human supervisor.")
        return {
            "status": "DISPATCHING",
            "execution_stage": "HUMAN_APPROVED"
        }
    else:
        app_logger.warning(f"[human_approval_node] Incident {state.incident_id} REJECTED by human supervisor.")
        return {
            "status": "REJECTED",
            "error_logs": state.error_logs + [{"node": "human_approval_node", "error": "Human supervisor rejected auto-dispatch."}]
        }


def hospital_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Hospital Agent dispatch (Stage 2 Parallel)."""
    try:
        sev = state.severity_analysis.get("severity_level", 2)
        res = hospital_agent.execute_sync(HospitalInput(
            latitude=state.latitude,
            longitude=state.longitude,
            severity_level=sev,
            patients_count=state.vision_analysis.get("victims_visible_count", 1) or 1
        ))
        return {"hospital_recommendation": res.model_dump()}
    except Exception as e:
        app_logger.error(f"[hospital_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "hospital_node", "error": str(e)}]
        }


def ambulance_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Ambulance Agent dispatch (Stage 2 Parallel)."""
    try:
        sev = state.severity_analysis.get("severity_level", 2)
        res = ambulance_agent.execute_sync(AmbulanceInput(
            latitude=state.latitude,
            longitude=state.longitude,
            severity_level=sev,
            required_units_count=max(1, state.vision_analysis.get("victims_visible_count", 1))
        ))
        return {"ambulance_assignment": res.model_dump()}
    except Exception as e:
        app_logger.error(f"[ambulance_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "ambulance_node", "error": str(e)}]
        }


def traffic_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Traffic Agent optimization (Stage 2 Parallel)."""
    try:
        res = traffic_agent.execute_sync(TrafficInput(
            origin_lat=state.latitude + 0.02,
            origin_lng=state.longitude + 0.02,
            destination_lat=state.latitude,
            destination_lng=state.longitude,
            incident_type="MEDICAL_EMERGENCY"
        ))
        return {"traffic_analysis": res.model_dump()}
    except Exception as e:
        app_logger.error(f"[traffic_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "traffic_node", "error": str(e)}]
        }


def communication_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Communication Agent payload generation."""
    try:
        units = []
        if state.ambulance_assignment and "assigned_units" in state.ambulance_assignment:
            units = [u.get("call_sign", "") for u in state.ambulance_assignment["assigned_units"]]
            
        hosp_name = None
        if state.hospital_recommendation and "primary_hospital" in state.hospital_recommendation:
            hosp_name = state.hospital_recommendation["primary_hospital"].get("hospital_name")
            
        res = communication_agent.execute_sync(CommunicationInput(
            incident_id=state.incident_id,
            summary=state.description,
            severity_level=state.severity_analysis.get("severity_level", 3),
            location=state.location_analysis.get("formatted_address", "Reported location"),
            hospital_name=hosp_name,
            assigned_units=units
        ))
        return {"communications": res.model_dump()}
    except Exception as e:
        app_logger.error(f"[communication_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "communication_node", "error": str(e)}]
        }


def report_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Report Agent compilation."""
    try:
        res = report_agent.execute_sync(ReportInput(
            incident_id=state.incident_id,
            tracking_code=state.tracking_code,
            description=state.description,
            severity=state.severity_analysis,
            location=state.location_analysis,
            hospital=state.hospital_recommendation,
            ambulance=state.ambulance_assignment,
            traffic=state.traffic_analysis,
            communications=state.communications
        ))
        return {
            "report": res.model_dump(),
            "execution_stage": "REPORT_GENERATED"
        }
    except Exception as e:
        app_logger.error(f"[report_node] Error: {e}")
        return {
            "error_logs": state.error_logs + [{"node": "report_node", "error": str(e)}]
        }


def memory_save_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Memory Agent session persistence."""
    res = memory_agent.execute_sync(MemoryInput(
        action="STORE",
        incident_id=state.incident_id,
        state_snapshot={"tracking_code": state.tracking_code, "status": state.status}
    ))
    return {
        "memory_logs": state.memory_logs + [res.model_dump()]
    }


def logger_end_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Logger Agent finalization log."""
    res = logger_agent.execute_sync(LoggerInput(
        node_name="logger_end",
        incident_id=state.incident_id,
        event_type="INFO",
        message="Workflow execution completed successfully."
    ))
    return {
        "status": "COMPLETED" if state.status != "RECOVERED" else "RECOVERED",
        "execution_stage": "COMPLETED",
        "audit_logs": state.audit_logs + [res.model_dump()]
    }


def recovery_node(state: EmergencyResponseState) -> Dict[str, Any]:
    """Node: Recovery Agent self-healing and error mitigation."""
    failed_node = state.error_logs[-1]["node"] if state.error_logs else "unknown"
    err_msg = state.error_logs[-1]["error"] if state.error_logs else "General graph exception"

    res = recovery_agent.execute_sync(RecoveryInput(
        incident_id=state.incident_id,
        failed_node=failed_node,
        error_message=err_msg,
        partial_state=state.model_dump()
    ))
    
    updates = res.repaired_state_updates
    updates["recovery_details"] = res.model_dump()
    updates["recovery_triggered"] = True
    return updates


# Helper monkeypatch to add execute_sync to BaseAgent for node synchronous calls
def _add_execute_sync():
    import asyncio
    from agents.base_agent import BaseAgent

    def execute_sync(self, input_data):
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                return self.fallback_execution(input_data)
            else:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.execute(input_data))
                finally:
                    new_loop.close()
        except Exception:
            return self.fallback_execution(input_data)

    BaseAgent.execute_sync = execute_sync

_add_execute_sync()


# ============================================================================
# Conditional Edge Routing Functions
# ============================================================================

def route_after_intake(state: EmergencyResponseState) -> str:
    """Conditional Edge: Routes after parallel intake (Vision + Location)."""
    if state.error_logs:
        return "recovery"
    return "severity"


def route_after_severity(state: EmergencyResponseState) -> str:
    """Conditional Edge: Routes after Severity rating to Supervisor."""
    if state.error_logs:
        return "recovery"
    return "supervisor"


def route_supervisor_decision(state: EmergencyResponseState) -> str:
    """Conditional Edge: Routes based on Supervisor output & severity level."""
    if state.error_logs:
        return "recovery"
        
    decision = state.supervisor_decision
    next_node = decision.get("next_node")
    
    if next_node == "human_approval" or state.human_approval_required:
        return "human_approval"
    elif next_node == "recovery":
        return "recovery"
    else:
        return "parallel_dispatch"


def route_after_human_approval(state: EmergencyResponseState) -> str:
    """Conditional Edge: Routes after Human Approval check."""
    if state.human_approval_granted is True or state.status == "DISPATCHING":
        return "parallel_dispatch"
    elif state.human_approval_granted is False or state.status == "REJECTED":
        return "recovery"
    else:
        # Paused / awaiting human input
        return "awaiting_approval_end"


def route_after_dispatch(state: EmergencyResponseState) -> str:
    """Conditional Edge: Routes after parallel dispatch to Communication."""
    if state.error_logs:
        return "recovery"
    return "communication"


# ============================================================================
# Graph Builder
# ============================================================================

def build_emergency_langgraph():
    """
    Constructs and compiles the complete 12-agent LangGraph workflow graph.
    """
    builder = StateGraph(EmergencyResponseState)

    # 1. Add all nodes
    builder.add_node("logger_start", logger_start_node)
    builder.add_node("memory_fetch", memory_fetch_node)
    builder.add_node("vision", vision_node)
    builder.add_node("location", location_node)
    builder.add_node("severity", severity_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("hospital", hospital_node)
    builder.add_node("ambulance", ambulance_node)
    builder.add_node("traffic", traffic_node)
    builder.add_node("communication", communication_node)
    builder.add_node("report", report_node)
    builder.add_node("memory_save", memory_save_node)
    builder.add_node("logger_end", logger_end_node)
    builder.add_node("recovery", recovery_node)

    # 2. Add Start & Linear Edges
    builder.add_edge(START, "logger_start")
    builder.add_edge("logger_start", "memory_fetch")

    # 3. Fan-out Stage 1 Parallel Intake (Vision & Location)
    builder.add_edge("memory_fetch", "vision")
    builder.add_edge("memory_fetch", "location")

    # 4. Fan-in Stage 1 to Severity
    builder.add_edge("vision", "severity")
    builder.add_edge("location", "severity")

    # 5. Route after Severity to Supervisor
    builder.add_conditional_edges("severity", route_after_severity, {
        "supervisor": "supervisor",
        "recovery": "recovery"
    })

    # 6. Route Supervisor Decision
    builder.add_conditional_edges("supervisor", route_supervisor_decision, {
        "human_approval": "human_approval",
        "parallel_dispatch": "hospital",
        "recovery": "recovery"
    })

    # Additional edges for parallel dispatch fan-out from supervisor
    builder.add_edge("supervisor", "ambulance")
    builder.add_edge("supervisor", "traffic")

    # 7. Route after Human Approval
    builder.add_conditional_edges("human_approval", route_after_human_approval, {
        "parallel_dispatch": "hospital",
        "recovery": "recovery",
        "awaiting_approval_end": END
    })

    # 8. Fan-in Stage 2 Parallel Dispatch to Communication
    builder.add_edge("hospital", "communication")
    builder.add_edge("ambulance", "communication")
    builder.add_edge("traffic", "communication")

    # 9. Final Pipeline Edges
    builder.add_edge("communication", "report")
    builder.add_edge("report", "memory_save")
    builder.add_edge("memory_save", "logger_end")
    builder.add_edge("logger_end", END)

    # 10. Recovery edges
    builder.add_edge("recovery", "hospital")
    builder.add_edge("recovery", "ambulance")

    # 11. Memory Checkpointer for state persistence
    checkpointer = MemorySaver()
    compiled_graph = builder.compile(checkpointer=checkpointer)
    return compiled_graph


# Global Compiled Graph Instance
emergency_response_graph = build_emergency_langgraph()


def run_emergency_workflow(
    incident_id: str,
    description: str,
    latitude: float,
    longitude: float,
    address_text: Optional[str] = None,
    image_urls: Optional[List[str]] = None,
    video_urls: Optional[List[str]] = None,
    human_approval_granted: Optional[bool] = None,
    thread_id: Optional[str] = None
) -> EmergencyResponseState:
    """
    Executes the LangGraph Emergency Response Workflow with state checkpointing.
    """
    tid = thread_id or f"thread-{incident_id}"
    config = {"configurable": {"thread_id": tid}}

    initial_state = EmergencyResponseState(
        incident_id=incident_id,
        tracking_code=f"EMG-{incident_id[:8].upper()}",
        description=description,
        latitude=latitude,
        longitude=longitude,
        address_text=address_text,
        image_urls=image_urls or [],
        video_urls=video_urls or [],
        human_approval_granted=human_approval_granted
    )

    final_state_dict = emergency_response_graph.invoke(initial_state.model_dump(), config=config)
    return EmergencyResponseState(**final_state_dict)
