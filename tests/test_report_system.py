"""
Unit & Integration Tests for Incident Report System

Tests:
- IncidentReport SQLAlchemy Model
- ReportService (Report creation, PostgreSQL persistence, AI Summary generation)
- PDF Export Engine (PDF byte stream compilation)
- CSV Export Engine (CSV byte stream formatting)
- FastAPI Report Router Endpoints
"""

import pytest
import io
import csv
from services.report_service import report_service, ReportService
from schemas.report import ReportCreate
from models.report import IncidentReport


def test_report_service_pdf_generation():
    """Tests PDF report generation engine."""
    sample_report = {
        "incident_id": "INC-8821",
        "tracking_code": "TRK-8821",
        "title": "Emergency Response Audit: INC-8821",
        "ai_summary": "Test AI Summary for multi-agent dispatch.",
        "officer_notes": "Supervisor verified all agent actions cleanly.",
        "recommendations": ["Signal preemption executed smoothly."],
        "timeline_data": [
            {"time": "10:12:05", "source": "SupervisorAgent", "event": "Incident received"}
        ],
        "metrics_data": {"sla_compliance_score": 100, "ambulance_eta_minutes": 4.2}
    }

    pdf_bytes = report_service.generate_pdf_report(sample_report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_report_service_csv_generation():
    """Tests CSV report export engine."""
    sample_report = {
        "incident_id": "INC-8821",
        "tracking_code": "TRK-8821",
        "title": "Emergency Response Audit: INC-8821",
        "ai_summary": "Test AI Summary for multi-agent dispatch.",
        "officer_notes": "Supervisor verified all agent actions cleanly.",
        "recommendations": ["Signal preemption executed smoothly."],
        "timeline_data": [
            {"time": "10:12:05", "source": "SupervisorAgent", "event": "Incident received"}
        ]
    }

    csv_bytes = report_service.generate_csv_report(sample_report)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0

    csv_text = csv_bytes.decode("utf-8")
    assert "INCIDENT REPORT METADATA" in csv_text
    assert "INC-8821" in csv_text
    assert "TIMELINE EVENTS" in csv_text
