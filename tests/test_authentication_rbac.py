"""
Unit & Integration Tests for JWT Authentication & Role-Based Access Control (RBAC)

Tests:
- JWT Access & Refresh Token Creation, Claims, & Expiration
- Token Verification (Access vs Refresh type enforcement)
- Role Definitions (Admin, Police, Hospital, Dispatcher, Viewer)
- RBAC Permission Enforcement (require_roles)
- Streamlit Auth Guard Role Matrix (get_allowed_pages, has_page_access)
"""

import pytest
from datetime import timedelta
from authentication.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_token,
    get_password_hash,
    verify_password
)
from authentication.rbac import Role, require_roles
from frontend.auth_guard import get_allowed_pages, has_page_access, ROLE_PERMISSIONS
from utils.exceptions import PermissionDeniedError


class DummyUser:
    """Mock User object for testing RBAC dependencies."""
    def __init__(self, role: str, email: str = "test@eoc.gov"):
        self.role = role
        self.email = email


def test_password_hashing():
    """Tests bcrypt password hashing and verification."""
    raw_pwd = "SecretPassword123!"
    hashed = get_password_hash(raw_pwd)

    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_access_and_refresh_token_lifecycle():
    """Tests JWT access and refresh token creation, decoding, and type verification."""
    claims = {"sub": "user-uuid-1234", "email": "officer@eoc.gov", "role": "dispatcher"}

    access_token = create_access_token(claims)
    refresh_token = create_refresh_token({"sub": "user-uuid-1234"})

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)

    # Verify access token
    acc_payload = verify_token(access_token, expected_type="access")
    assert acc_payload is not None
    assert acc_payload["sub"] == "user-uuid-1234"
    assert acc_payload["role"] == "dispatcher"
    assert acc_payload["token_type"] == "access"

    # Verify refresh token
    ref_payload = verify_token(refresh_token, expected_type="refresh")
    assert ref_payload is not None
    assert ref_payload["sub"] == "user-uuid-1234"
    assert ref_payload["token_type"] == "refresh"

    # Cross-type verification should fail
    assert verify_token(access_token, expected_type="refresh") is None
    assert verify_token(refresh_token, expected_type="access") is None


def test_rbac_roles_enum():
    """Tests Role Enum values."""
    assert Role.ADMIN == "admin"
    assert Role.POLICE == "police"
    assert Role.HOSPITAL == "hospital"
    assert Role.DISPATCHER == "dispatcher"
    assert Role.VIEWER == "viewer"


@pytest.mark.asyncio
async def test_require_roles_dependency():
    """Tests require_roles dependency for authorized and unauthorized roles."""
    admin_user = DummyUser(role="admin")
    dispatcher_user = DummyUser(role="dispatcher")
    viewer_user = DummyUser(role="viewer")

    checker = require_roles([Role.DISPATCHER, Role.POLICE])

    # Dispatcher is explicitly allowed
    res_disp = await checker(dispatcher_user)
    assert res_disp.role == "dispatcher"

    # Admin is implicitly allowed via override
    res_admin = await checker(admin_user)
    assert res_admin.role == "admin"

    # Viewer should be rejected with PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        await checker(viewer_user)


def test_streamlit_auth_guard_role_matrix():
    """Tests frontend Streamlit auth guard role permission matrix."""
    # Admin gets all 11 pages
    admin_pages = get_allowed_pages("admin")
    assert len(admin_pages) == 11
    assert has_page_access("admin", "Settings") is True

    # Dispatcher gets 10 pages (no Settings)
    disp_pages = get_allowed_pages("dispatcher")
    assert len(disp_pages) == 10
    assert has_page_access("dispatcher", "Settings") is False
    assert has_page_access("dispatcher", "Dashboard") is True

    # Police gets 9 pages
    police_pages = get_allowed_pages("police")
    assert len(police_pages) == 9
    assert has_page_access("police", "Hospital Dashboard") is False
    assert has_page_access("police", "Live Camera") is True

    # Hospital gets 5 pages
    hosp_pages = get_allowed_pages("hospital")
    assert len(hosp_pages) == 5
    assert has_page_access("hospital", "Hospital Dashboard") is True
    assert has_page_access("hospital", "Ambulance Dashboard") is False

    # Viewer gets 3 pages
    viewer_pages = get_allowed_pages("viewer")
    assert len(viewer_pages) == 3
    assert has_page_access("viewer", "Dashboard") is True
    assert has_page_access("viewer", "Incident Details") is False
