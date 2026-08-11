"""
FastAPI Integration API Endpoints Test Suite

Tests:
- Health Router (/health)
- Hospitals Router (/api/v1/hospitals/)
- Reports Router (/api/v1/reports/)
- Notifications Router (/api/v1/notifications/)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Tests /health endpoint response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "ok", "HEALTHY")


def test_hospitals_endpoints():
    """Tests /api/v1/hospitals/ endpoints."""
    # List hospitals
    res_list = client.get("/api/v1/hospitals/")
    assert res_list.status_code == 200
    hospitals = res_list.json()
    assert isinstance(hospitals, list)
    assert len(hospitals) > 0

    # Get hospital by ID
    hosp_id = hospitals[0]["hospital_id"]
    res_single = client.get(f"/api/v1/hospitals/{hosp_id}")
    assert res_single.status_code == 200
    assert res_single.json()["hospital_id"] == hosp_id

    # Reserve bed
    res_bed = client.post(f"/api/v1/hospitals/{hosp_id}/reserve-bed")
    assert res_bed.status_code in (200, 400)


def test_reports_endpoints():
    """Tests /api/v1/reports/ endpoints."""
    # Analytics
    res_analytics = client.get("/api/v1/reports/analytics?time_horizon=24h")
    assert res_analytics.status_code == 200
    data = res_analytics.json()
    assert "daily_incidents" in data
    assert "severity_breakdown" in data

    # Compliance audit
    res_comp = client.get("/api/v1/reports/INC-8821/compliance")
    assert res_comp.status_code == 200
    assert res_comp.json()["sla_compliance_score"] == 100

    # PDF Export
    res_pdf = client.get("/api/v1/reports/export/pdf?incident_id=INC-8821")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"

    # CSV Export
    res_csv = client.get("/api/v1/reports/export/csv?incident_id=INC-8821")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]


def test_notifications_endpoints():
    """Tests /api/v1/notifications/ endpoints."""
    # List notifications
    res_notif = client.get("/api/v1/notifications/")
    assert res_notif.status_code == 200
    assert isinstance(res_notif.json(), list)

    # Dispatcher alert
    res_alert = client.post(
        "/api/v1/notifications/dispatcher-alert",
        json={"message": "Test alert", "priority": "HIGH"}
    )
    assert res_alert.status_code == 200
    assert res_alert.json()["status"] == "DELIVERED"

    # Public SMS broadcast
    res_sms = client.post(
        "/api/v1/notifications/public-sms",
        json={"sector": "Sector 4", "alert_text": "Evacuation advisory", "severity": "WARNING"}
    )
    assert res_sms.status_code == 200
    assert res_sms.json()["status"] == "BROADCAST_SENT"
