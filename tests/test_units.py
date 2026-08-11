"""
Responder Units API Integration Tests
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_responder_unit_lifecycle(client: AsyncClient):
    """Test unit registration, telemetry pinging, and status updates."""
    # 1. Register admin user
    await client.post("/api/v1/auth/register", json={
        "email": "admin@emergency.gov",
        "full_name": "System Admin",
        "password": "AdminPassword123!",
        "role": "admin"
    })
    login_res = await client.post("/api/v1/auth/login", data={
        "username": "admin@emergency.gov",
        "password": "AdminPassword123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register new responder unit
    unit_payload = {
        "call_sign": "AMB-911",
        "unit_type": "ambulance",
        "current_lat": 37.7749,
        "current_lon": -122.4194
    }
    create_res = await client.post("/api/v1/units/", json=unit_payload, headers=headers)
    assert create_res.status_code == 201
    unit_data = create_res.json()
    assert unit_data["call_sign"] == "AMB-911"
    unit_id = unit_data["id"]

    # 3. Update telemetry ping
    telemetry_payload = {"current_lat": 37.7755, "current_lon": -122.4180}
    telem_res = await client.post(f"/api/v1/units/{unit_id}/telemetry", json=telemetry_payload, headers=headers)
    assert telem_res.status_code == 200
    assert telem_res.json()["current_lat"] == 37.7755

    # 4. Update status
    status_res = await client.patch(f"/api/v1/units/{unit_id}/status", json={"status": "en_route"}, headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "en_route"
