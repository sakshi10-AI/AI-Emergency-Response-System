"""
User Model Definition
"""
from sqlalchemy import Column, String, Boolean, DateTime, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="citizen") # admin, dispatcher, responder, citizen
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    incidents = relationship("Incident", back_populates="reporter", cascade="save-update, merge")
    assigned_units = relationship("ResponderUnit", back_populates="assigned_user")
