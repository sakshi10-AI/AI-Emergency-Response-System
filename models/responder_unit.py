"""
Responder Unit Model Definition
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base

class ResponderUnit(Base):
    __tablename__ = "responder_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_sign = Column(String(50), unique=True, index=True, nullable=False)
    unit_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="available")
    current_lat = Column(Float, nullable=False)
    current_lon = Column(Float, nullable=False)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_ping = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    assigned_user = relationship("User", back_populates="assigned_units")
    assignments = relationship("DispatchAssignment", back_populates="unit")
