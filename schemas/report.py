"""
Incident Report Schemas (DTOs)

Defines request and response schemas for creating, updating, and exporting formal reports.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID


class ReportCreate(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier")
    tracking_code: Optional[str] = Field(None, description="Human readable tracking code")
    title: Optional[str] = Field(None, description="Report headline title")
    officer_notes: Optional[str] = Field(None, description="Manual officer/supervisor notes")
    custom_recommendations: Optional[List[str]] = Field(default_factory=list, description="Custom officer recommendations")


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    officer_notes: Optional[str] = None
    recommendations: Optional[List[str]] = None


class ReportResponse(BaseModel):
    id: UUID
    incident_id: str
    tracking_code: str
    title: str
    ai_summary: Optional[str] = None
    officer_notes: Optional[str] = None
    recommendations: List[Any] = Field(default_factory=list)
    timeline_data: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_images: List[Dict[str, Any]] = Field(default_factory=list)
    metrics_data: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
