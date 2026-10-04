"""
Hospital Call Log Model Definition

Tracks automated and manual voice dispatch calls placed to regional hospitals
during emergencies, recording timestamps, target phone numbers, synthetic audio transcripts,
call status, and response latency.
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, UUID, func
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base


class HospitalCallLog(Base):
    __tablename__ = "hospital_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Destination Phone & Telephony Info
    target_phone = Column(String(50), nullable=False, default="7796119389", index=True)
    caller_callerid = Column(String(50), nullable=False, default="Nagpur EOC Dispatch (+91-712-EOC-AI)")
    call_type = Column(String(50), nullable=False, default="AUTOMATED_EMERGENCY_DISPATCH")
    status = Column(String(50), nullable=False, default="INITIATED", index=True) # INITIATED, RINGING, CONNECTED, COMPLETED, FAILED
    
    # Emergency Call Payload
    speech_transcript = Column(Text, nullable=False)
    distance_km = Column(Float, nullable=True)
    eta_minutes = Column(Float, nullable=True)
    casualties_count = Column(Integer, nullable=False, default=1)
    severity_level = Column(Integer, nullable=False, default=1)
    
    # Metrics
    duration_seconds = Column(Integer, nullable=False, default=0)
    provider_call_id = Column(String(100), nullable=True) # Twilio SID or Telephony reference
    response_code = Column(String(50), nullable=True)
    
    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="call_logs")
    hospital = relationship("Hospital", back_populates="call_logs")
