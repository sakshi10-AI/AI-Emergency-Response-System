"""
User Domain & CRUD Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from schemas.user import UserCreate
from authentication.jwt import get_password_hash, verify_password
from utils.exceptions import ResourceNotFoundError, CustomAppException

class UserService:
    """Handles User CRUD operations and authentication lookup."""

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Fetch user record by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """Create new user with hashed password."""
        existing = await self.get_by_email(db, user_in.email)
        if existing:
            raise CustomAppException("User with this email already exists", status_code=400, error_code="USER_ALREADY_EXISTS")

        hashed_pwd = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_pwd,
            full_name=user_in.full_name,
            role=user_in.role
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> User | None:
        """Authenticate user against stored bcrypt password hash."""
        user = await self.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

user_service = UserService()
