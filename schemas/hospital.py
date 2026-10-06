"""
Hospital & Emergency Call Validation Schemas (DTOs)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class HospitalBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    emergency_phone: str = Field("7796119389", max_length=50, description="Hospital Emergency Desk Phone")
    alternate_phone: Optional[str] = Field(None, max_length=50)
    trauma_level: str = Field("Level I", max_length=50)
    address: str
    city: str = Field("Nagpur", max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    total_icu_beds: int = Field(40, ge=0)
    available_icu_beds: int = Field(10, ge=0)
    total_emergency_beds: int = Field(80, ge=0)
    available_emergency_beds: int = Field(20, ge=0)
    er_occupancy_percent: int = Field(70, ge=0, le=100)
    specialties: List[str] = Field(default_factory=list)
    status: str = Field("OPEN", max_length=50)
    is_active: bool = True


class HospitalCreate(HospitalBase):
    pass


class HospitalResponse(HospitalBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmergencyCallDispatchRequest(BaseModel):
    incident_id: UUID
    target_phone: Optional[str] = Field("7796119389", description="Destination hospital emergency phone (defaults to 7796119389)")
    custom_speech_text: Optional[str] = None


class EmergencyCallResponse(BaseModel):
    id: UUID
    incident_id: UUID
    hospital_id: UUID
    target_phone: str
    caller_callerid: str
    call_type: str
    status: str
    speech_transcript: str
    distance_km: Optional[float] = None
    eta_minutes: Optional[float] = None
    casualties_count: int
    severity_level: int
    duration_seconds: int
    provider_call_id: Optional[str] = None
    response_code: Optional[str] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
