"""
End-to-End System Integration Test Suite

Simulates full multi-agent pipeline execution:
1. Computer Vision detection (Camera Feed / Frame -> Hazard Detection)
2. Severity Assessment & Priority Categorization (Triage Level 1)
3. Trauma Hospital Selection & Bed Reservation (SF General Level I)
4. ALS Ambulance Dispatch & GPS Tracking (Medic 101, ETA 4.2m)
5. Traffic Signal Preemption (Corridor preemption)
6. PostgreSQL Post-Incident Report Generation
7. Redis Workflow Checkpoint State Storage
"""

import pytest
import asyncio
from vision import vision_detection_service, YOLOv11Detector
from agents import SeverityAgent, HospitalAgent, AmbulanceAgent, TrafficAgent
from agents.langgraph_agents import AgentTools
from services.report_service import report_service
from memory.checkpoint_manager import StateCheckpointManager


@pytest.mark.asyncio
async def test_end_to_end_emergency_response_pipeline():
    """Simulates full emergency response pipeline execution from detection to report export."""

    # 1. Computer Vision Hazard Detection
    detector = YOLOv11Detector()
    detected_objects = detector.predict("test_frame.jpg", confidence_threshold=0.45)
    assert isinstance(detected_objects, list)
    assert len(detected_objects) > 0

    # 2. Severity Triage Assessment
    triage_result = AgentTools.compute_severity_index("Active multi-vehicle fire and rollover", has_fire=True, victim_count=4)
    assert triage_result["severity_level"] in (1, 2)
    assert triage_result["priority_category"] in ("IMMEDIATE", "URGENT")

    # 3. Hospital Routing & ICU Reservation
    hosp_selection = AgentTools.query_hospital_beds(37.7749, -122.4194, triage_result["severity_level"])
    assert hosp_selection["primary"]["hospital_name"] is not None
    assert hosp_selection["primary"]["available_icu_beds"] > 0

    # 4. Ambulance Dispatch & Routing
    ems_units = AgentTools.allocate_ems_units(37.7749, -122.4194, count=1)
    assert len(ems_units) > 0
    assert ems_units[0]["unit_id"] is not None
    assert ems_units[0]["eta_minutes"] > 0

    # 5. Traffic Signal Preemption
    traffic_res = AgentTools.analyze_traffic_routes(37.7749, -122.4194, 37.7833, -122.4167)
    assert traffic_res["signals_preempted"] is True

    # 6. PDF & CSV Report Generation
    report_dict = {
        "incident_id": "INC-E2E-9901",
        "tracking_code": "TRK-E2E-9901",
        "title": "End-to-End Test Incident Report",
        "ai_summary": f"Vision detected hazards ({[obj.label for obj in detected_objects]}). Assigned {triage_result['priority_category']} priority. Hospital {hosp_selection['primary']['hospital_name']} selected. Dispatched {ems_units[0]['call_sign']}.",
        "officer_notes": "E2E pipeline executed flawlessly.",
        "recommendations": ["Corridor preemption executed in 1.2 seconds."],
        "timeline_data": [
            {"time": "10:00:00", "source": "VisionAgent", "event": "Detected active fire"},
            {"time": "10:00:02", "source": "SeverityAgent", "event": "Assigned CRITICAL priority"},
            {"time": "10:00:05", "source": "HospitalAgent", "event": "Selected SF General"},
            {"time": "10:00:08", "source": "AmbulanceAgent", "event": "Dispatched AMB-101"}
        ]
    }

    pdf_bytes = report_service.generate_pdf_report(report_dict)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

    csv_bytes = report_service.generate_csv_report(report_dict)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0

    # 7. Checkpoint Storage
    chk_mgr = StateCheckpointManager()
    chk_id = chk_mgr.create_checkpoint(
        domain="incident",
        entity_id="INC-E2E-9901",
        label="COMPLETED",
        state_data={
            "dispatch_plan": ems_units,
            "hospital_selection": hosp_selection
        }
    )
    assert chk_id is not None
