"""
Incident Report Model Definition for PostgreSQL Persistence

Stores formal post-incident audit reports, AI summaries, officer notes,
evidence image metadata, timeline events, and SLA compliance metrics.
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from database.connection import Base


class IncidentReport(Base):
    """SQLAlchemy model for storing formal incident reports in PostgreSQL."""
    __tablename__ = "incident_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(String(100), index=True, nullable=False)
    tracking_code = Column(String(50), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    ai_summary = Column(Text, nullable=True)
    officer_notes = Column(Text, nullable=True)
    recommendations = Column(JSON, nullable=True)  # List of strings/dicts
    timeline_data = Column(JSON, nullable=True)     # List of timeline event dicts
    evidence_images = Column(JSON, nullable=True)   # List of image URLs/captions
    metrics_data = Column(JSON, nullable=True)      # SLA compliance metrics dict
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User")
