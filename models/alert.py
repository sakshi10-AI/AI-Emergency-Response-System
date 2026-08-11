"""
Public Alert Model Definition
"""
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base

class PublicAlert(Base):
    __tablename__ = "public_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False, default="warning")
    target_radius_km = Column(Float, default=5.0)
    center_lat = Column(Float, nullable=True)
    center_lon = Column(Float, nullable=True)
    broadcast_status = Column(String(50), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    incident = relationship("Incident", back_populates="alerts")
