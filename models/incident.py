"""
Incident Model Definition
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_code = Column(String(50), unique=True, index=True, nullable=False)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(50), nullable=False, default="other")
    severity = Column(Integer, nullable=False, default=3)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="reported")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address_text = Column(Text, nullable=True)
    triage_summary = Column(Text, nullable=True)
    threat_assessment = Column(Text, nullable=True)
    assigned_hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    reporter = relationship("User", back_populates="incidents")
    assigned_hospital = relationship("Hospital", back_populates="incidents")
    dispatches = relationship("DispatchAssignment", back_populates="incident", cascade="all, delete-orphan")
    alerts = relationship("PublicAlert", back_populates="incident")
    call_logs = relationship("HospitalCallLog", back_populates="incident", cascade="all, delete-orphan")
