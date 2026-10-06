"""
Hospital Model Definition

Stores regional trauma centers, ICU capacities, specialty departments,
and emergency dispatch contact numbers for automated incident alerts.
"""
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, JSON, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    emergency_phone = Column(String(50), nullable=False, default="7796119389")
    alternate_phone = Column(String(50), nullable=True)
    trauma_level = Column(String(50), index=True, nullable=False, default="Level I") # Level I, Level II, Level III
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, default="Nagpur")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Capacity Metrics
    total_icu_beds = Column(Integer, nullable=False, default=40)
    available_icu_beds = Column(Integer, nullable=False, default=10)
    total_emergency_beds = Column(Integer, nullable=False, default=80)
    available_emergency_beds = Column(Integer, nullable=False, default=20)
    er_occupancy_percent = Column(Integer, nullable=False, default=70)
    
    # Metadata & Departments
    specialties = Column(JSON, nullable=True, default=list) # e.g. ["Trauma", "Burn", "Neuro", "Cardiac"]
    status = Column(String(50), nullable=False, default="OPEN", index=True) # OPEN, BUSY, DIVERT, FULL
    is_active = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    incidents = relationship("Incident", back_populates="assigned_hospital")
    call_logs = relationship("HospitalCallLog", back_populates="hospital", cascade="all, delete-orphan")
