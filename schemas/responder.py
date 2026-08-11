"""
Responder Unit Validation Schemas (DTOs)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class ResponderUnitCreate(BaseModel):
    call_sign: str = Field(..., min_length=2, max_length=50)
    unit_type: str = Field(..., description="ambulance, fire_truck, police_cruiser, hazmat_unit, rescue_helicopter")
    current_lat: float
    current_lon: float

class ResponderUnitTelemetry(BaseModel):
    current_lat: float
    current_lon: float

class ResponderUnitStatusUpdate(BaseModel):
    status: str = Field(..., description="available, dispatched, en_route, on_scene, out_of_service")

class ResponderUnitResponse(BaseModel):
    id: UUID
    call_sign: str
    unit_type: str
    status: str
    current_lat: float
    current_lon: float
    last_ping: datetime

    model_config = ConfigDict(from_attributes=True)
