"""
Incidents API Integration Tests
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_report_and_list_incidents(client: AsyncClient):
    """Test reporting an emergency incident and listing incidents with role permissions."""
    # 1. Report incident
    incident_payload = {
        "description": "Structure fire reported on 5th floor with smoke visible",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address_text": "550 Market St, San Francisco, CA"
    }
    report_res = await client.post("/api/v1/incidents/", json=incident_payload)
    assert report_res.status_code == 201
    incident_data = report_res.json()
    assert incident_data["description"] == incident_payload["description"]
    assert "tracking_code" in incident_data

    # 2. Register and login dispatcher user
    reg_user = await client.post("/api/v1/auth/register", json={
        "email": "dispatcher1@emergency.gov",
        "full_name": "Dispatcher One",
        "password": "Password123!",
        "role": "dispatcher"
    })
    assert reg_user.status_code == 201

    login_res = await client.post("/api/v1/auth/login", data={
        "username": "dispatcher1@emergency.gov",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. List incidents with dispatcher token
    list_res = await client.get("/api/v1/incidents/", headers=headers)
    assert list_res.status_code == 200
    incidents_list = list_res.json()
    assert len(incidents_list) >= 1
    assert incidents_list[0]["id"] == incident_data["id"]
