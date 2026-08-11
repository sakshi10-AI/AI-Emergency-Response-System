"""
Dispatch Assignment Model Definition
"""
from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base

class DispatchAssignment(Base):
    __tablename__ = "dispatch_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("responder_units.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="assigned")
    assigned_by_agent = Column(Boolean, default=True)
    agent_reasoning = Column(Text, nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="dispatches")
    unit = relationship("ResponderUnit", back_populates="assignments")
