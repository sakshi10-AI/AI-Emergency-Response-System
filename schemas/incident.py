"""
Incident Validation Schemas (DTOs)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class IncidentCreate(BaseModel):
    description: str = Field(..., min_length=5, description="Caller emergency description")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate")
    address_text: Optional[str] = Field(None, description="Human readable address")

class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., description="Status: reported, triaged, dispatched, in_progress, resolved, cancelled")

class IncidentResponse(BaseModel):
    id: UUID
    tracking_code: str
    category: str
    severity: int
    description: str
    status: str
    latitude: float
    longitude: float
    address_text: Optional[str] = None
    triage_summary: Optional[str] = None
    threat_assessment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
