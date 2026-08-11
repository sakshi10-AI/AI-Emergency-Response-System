"""
Role-Based Access Control (RBAC) & Authentication Dependencies

Provides FastAPI Depends dependencies for extracting current user and enforcing role permissions.
Roles supported: Admin, Police, Hospital, Dispatcher, Viewer.
"""

from enum import Enum
from typing import List, Optional
import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import get_db
from authentication.jwt import verify_token
from models.user import User
from utils.exceptions import AuthenticationError, PermissionDeniedError


class Role(str, Enum):
    """System Roles Enum for Role-Based Access Control."""
    ADMIN = "admin"
    POLICE = "police"
    HOSPITAL = "hospital"
    DISPATCHER = "dispatcher"
    VIEWER = "viewer"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency: Extracts, validates JWT token, and retrieves current user from DB."""
    payload = verify_token(token, expected_type="access")
    if not payload:
        raise AuthenticationError("Invalid or expired access token")

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token payload missing subject identifier")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid user ID format in token")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()

    if not user:
        raise AuthenticationError("User associated with token does not exist")
    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Dependency: Retrieves user if token is provided, otherwise returns None for anonymous access."""
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except Exception:
        return None


def require_roles(allowed_roles: List[str]):
    """Higher-order dependency enforcing user role permissions."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.lower() if current_user.role else "viewer"
        allowed_lower = [r.lower() for r in allowed_roles]

        # Admin role overrides all permissions
        if user_role == Role.ADMIN or user_role in allowed_lower:
            return current_user

        raise PermissionDeniedError(
            f"Action requires one of the following roles: {allowed_roles}. Your role: '{current_user.role}'"
        )
    return role_checker
