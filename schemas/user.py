"""
User Validation Schemas (DTOs)
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field("citizen", description="Role: admin, dispatcher, responder, citizen")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Plaintext user password")

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str
