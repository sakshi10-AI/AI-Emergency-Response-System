"""
Agent Audit Log Model Definition
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UUID, func, JSON
import uuid
from database.connection import Base

class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True)
    action_taken = Column(String(255), nullable=False)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    input_payload = Column(JSON, nullable=True)
    output_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
