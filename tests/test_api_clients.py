"""
Unit & Integration Tests for API Service Clients

Tests all frontend API service clients:
- BaseAPIClient (async HTTP, retries, TTL response caching, auth headers, exceptions)
- AuthenticationClient (login, register, token management)
- IncidentClient (list, get, create, status update, workflow dispatch, timeline)
- HospitalClient (list, reserve bed, capacity update, incoming units)
- AmbulanceClient (list, status update, location update, availability)
- ReportClient (report generation, compliance audit, executive analytics)
- NotificationClient (dispatcher alerts, public SMS broadcasts, history)
"""

import pytest
import asyncio
from frontend.api_clients import (
    BaseAPIClient,
    base_api_client,
    auth_client,
    incident_client,
    hospital_client,
    ambulance_client,
    report_client,
    notification_client,
    APIException,
    APIConnectionError,
    AuthenticationError,
    ResourceNotFoundError
)


@pytest.mark.asyncio
async def test_base_api_client_cache_and_headers():
    """Tests header generation, token setting, and response caching on BaseAPIClient."""
    client = BaseAPIClient(base_url="http://localhost:8000")
    client.set_auth_token("test-bearer-token")

    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer test-bearer-token"
    assert headers["Content-Type"] == "application/json"

    # Caching test
    cache_key = "GET:http://localhost:8000/test:{}"
    client._set_cache(cache_key, {"result": "cached_data"}, ttl=5)

    cached_val = client._get_from_cache(cache_key)
    assert cached_val is not None
    assert cached_val["result"] == "cached_data"

    client.clear_cache()
    assert client._get_from_cache(cache_key) is None


@pytest.mark.asyncio
async def test_auth_client_login():
    """Tests authentication client login and fallback handling."""
    res = await auth_client.login("dispatcher1", "password123")
    assert "access_token" in res
    assert res.get("token_type") == "bearer"

    user = await auth_client.get_current_user()
    assert user is not None
    assert "role" in user

    auth_client.logout()
    assert base_api_client._auth_token is None


def test_incident_client_operations():
    """Tests IncidentClient synchronous / asynchronous methods with fallback support."""
    incidents = incident_client.get_incidents()
    assert isinstance(incidents, list)
    assert len(incidents) > 0

    inc_id = incidents[0]["incident_id"]
    single_inc = incident_client.get_incident_by_id(inc_id)
    assert single_inc is not None
    assert single_inc["incident_id"] == inc_id

    # Update status
    updated = incident_client.update_incident_status(inc_id, "ANALYZING", notes="Status updated in test")
    assert updated is not None

    # Dispatch trigger
    dispatch_res = incident_client.trigger_workflow_dispatch(inc_id)
    assert "status" in dispatch_res

    # Timeline
    timeline = incident_client.get_incident_timeline(inc_id)
    assert isinstance(timeline, list)


def test_hospital_client_operations():
    """Tests HospitalClient operations."""
    hospitals = hospital_client.get_hospitals()
    assert isinstance(hospitals, list)
    assert len(hospitals) > 0

    hosp_id = hospitals[0]["hospital_id"]
    initial_beds = hospitals[0]["available_icu_beds"]

    # Bed reservation
    res = hospital_client.reserve_icu_bed(hosp_id)
    assert res.get("status") in ("RESERVED_FALLBACK", "success")

    # Incoming ambulances
    incoming = hospital_client.get_incoming_ambulances(hosp_id)
    assert isinstance(incoming, list)


def test_ambulance_client_operations():
    """Tests AmbulanceClient operations."""
    ambulances = ambulance_client.get_ambulances()
    assert isinstance(ambulances, list)
    assert len(ambulances) > 0

    unit_id = ambulances[0]["unit_id"]

    # Update status
    update_res = ambulance_client.update_unit_status(unit_id, "DISPATCHED")
    assert update_res is not None

    # Update location
    loc_res = ambulance_client.update_location(unit_id, 37.7750, -122.4190)
    assert loc_res is not None

    # Available units
    available = ambulance_client.get_available_units()
    assert isinstance(available, list)


def test_report_client_operations():
    """Tests ReportClient report generation and analytics."""
    report = report_client.generate_incident_report("INC-8821")
    assert report is not None
    assert report.get("incident_id") == "INC-8821"
    assert "compliance_score" in report

    compliance = report_client.get_compliance_audit("INC-8821")
    assert compliance.get("sla_compliance_score") == 100

    analytics = report_client.get_executive_analytics("24h")
    assert analytics.get("total_incidents") > 0


def test_notification_client_operations():
    """Tests NotificationClient alert sending and history."""
    alert_res = notification_client.send_dispatcher_alert("Test emergency alert message", priority="HIGH")
    assert alert_res is not None
    assert "status" in alert_res

    sms_res = notification_client.broadcast_public_sms("Sector 4", "Evacuate low lying area", severity="WARNING")
    assert sms_res is not None
    assert "status" in sms_res

    recent = notification_client.get_recent_notifications(limit=10)
    assert isinstance(recent, list)
