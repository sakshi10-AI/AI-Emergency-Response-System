"""
Authentication & Authorization API Integration Tests
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient):
    """Test user registration, login JWT token generation, and profile fetch."""
    # 1. Register new user
    register_payload = {
        "email": "testdispatcher@emergency.gov",
        "full_name": "Chief Dispatcher Jane",
        "password": "SecurePassword123!",
        "role": "dispatcher"
    }
    reg_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["email"] == "testdispatcher@emergency.gov"
    assert user_data["role"] == "dispatcher"

    # 2. Login to obtain JWT
    login_form = {
        "username": "testdispatcher@emergency.gov",
        "password": "SecurePassword123!"
    }
    login_response = await client.post("/api/v1/auth/login", data=login_form)
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 3. Access authenticated GET /me
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "testdispatcher@emergency.gov"

    # 4. Exchange refresh token for a new access token
    refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token_data["refresh_token"]})
    assert refresh_response.status_code == 200
    refreshed_data = refresh_response.json()
    assert "access_token" in refreshed_data
    assert "refresh_token" in refreshed_data
    assert refreshed_data["token_type"] == "bearer"
