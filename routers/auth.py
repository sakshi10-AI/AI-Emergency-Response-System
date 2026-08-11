"""
Authentication API Router

Handles user registration, login authentication, JWT access and refresh token issuance,
token refresh, and current user profile retrieval.
"""
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from schemas.user import UserCreate, UserResponse
from schemas.token import Token, TokenRefreshRequest
from services.user_service import user_service
from authentication.jwt import create_access_token, create_refresh_token, verify_token
from authentication.rbac import get_current_user
from models.user import User
from utils.exceptions import AuthenticationError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user (Admin, Police, Hospital, Dispatcher, Viewer) with hashed credentials."""
    return await user_service.create_user(db, user_in)


@router.post("/login", response_model=Token, summary="User login for OAuth2 token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticates credentials and returns signed JWT access and refresh tokens."""
    user = await user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise AuthenticationError("Incorrect email or password")

    claims = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(data=claims)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_access_token(
    req: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Exchanges a valid refresh token for a fresh access token."""
    payload = verify_token(req.refresh_token, expected_type="refresh")
    if not payload:
        raise AuthenticationError("Invalid or expired refresh token")

    user_id_str = payload.get("sub")
    user = await user_service.get_user_by_id(db, user_id_str)
    if not user or not user.is_active:
        raise AuthenticationError("User associated with refresh token is invalid or inactive")

    claims = {"sub": str(user.id), "email": user.email, "role": user.role}
    new_access_token = create_access_token(data=claims)
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse, summary="Get current logged-in user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return current_user
