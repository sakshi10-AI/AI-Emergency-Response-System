"""
Redis Memory Configuration

Defines Redis host, port, DB selection, password, connection timeouts,
key prefixes, and domain-specific Time-To-Live (TTL) expiration policies.
"""

from typing import Optional
from pydantic import BaseModel, Field


class RedisMemoryConfig(BaseModel):
    """Configuration settings for Redis Memory layer."""

    # Connection Parameters
    redis_host: str = Field(default="localhost", description="Redis server host")
    redis_port: int = Field(default=6379, description="Redis server port")
    redis_db: int = Field(default=0, description="Redis DB index")
    redis_password: Optional[str] = Field(default=None, description="Redis authentication password")
    socket_timeout: float = Field(default=2.0, description="Socket connection timeout in seconds")

    # Time-To-Live (TTL) Policies (in seconds)
    workflow_ttl: int = Field(default=86400, description="Workflow state TTL (24 hours)")
    incident_ttl: int = Field(default=604800, description="Incident state TTL (7 days)")
    agent_memory_ttl: int = Field(default=172800, description="Agent interaction memory TTL (48 hours)")
    session_ttl: int = Field(default=86400, description="User/Dispatcher session TTL (24 hours)")
    task_queue_ttl: int = Field(default=86400, description="Task queue message TTL (24 hours)")
    checkpoint_ttl: int = Field(default=604800, description="State Checkpoints TTL (7 days)")

    # Key Prefixes for Modular Stores
    workflow_prefix: str = Field(default="workflow:", description="Prefix for workflow state keys")
    incident_prefix: str = Field(default="incident:", description="Prefix for incident state keys")
    agent_prefix: str = Field(default="agent:", description="Prefix for agent memory keys")
    session_prefix: str = Field(default="session:", description="Prefix for session keys")
    task_queue_prefix: str = Field(default="task_queue:", description="Prefix for task queue keys")
    checkpoint_prefix: str = Field(default="checkpoint:", description="Prefix for state checkpoint keys")

    # Memory Limits
    max_agent_memory_messages: int = Field(default=50, description="Max rolling messages stored per agent")
    max_checkpoints_per_entity: int = Field(default=10, description="Maximum stored checkpoints per entity")


redis_config = RedisMemoryConfig()

