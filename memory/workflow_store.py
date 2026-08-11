"""
Redis Workflow State Store & Recovery Manager

Saves, loads, and recovers serialized LangGraph workflow states (EmergencyResponseState)
using thread IDs and incident IDs. Implements state persistence, TTL management,
checkpoint snapshots, and crash recovery.
"""

import time
import json
from typing import Optional, Dict, Any, List
from memory.redis_client import redis_client, RedisClient
from memory.config import redis_config
from agents.langgraph_schemas import EmergencyResponseState
from utils.logger import app_logger


import uuid


class RedisWorkflowStore:
    """Manages workflow state persistence, checkpoints, and recovery in Redis."""


    def __init__(self, client: Optional[RedisClient] = None):
        self.client = client or redis_client
        self.ttl = redis_config.workflow_ttl
        self.prefix = redis_config.workflow_prefix

    def _make_key(self, identifier: str) -> str:
        """Constructs Redis key for workflow state."""
        return f"{self.prefix}state:{identifier}"

    def _make_sec_key(self, incident_id: str) -> str:
        """Constructs secondary Redis key for incident to thread lookup."""
        return f"{self.prefix}incident:{incident_id}"

    def _make_checkpoint_key(self, thread_id: str, checkpoint_id: str) -> str:
        """Constructs checkpoint key for workflow."""
        return f"{redis_config.checkpoint_prefix}workflow:{thread_id}:{checkpoint_id}"

    def _make_checkpoint_list_key(self, thread_id: str) -> str:
        """Constructs key tracking checkpoint index list for thread."""
        return f"{redis_config.checkpoint_prefix}workflow:index:{thread_id}"

    def save_workflow_state(
        self,
        state: EmergencyResponseState,
        thread_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Saves serialized EmergencyResponseState into Redis with TTL.
        """
        tid = thread_id or f"thread-{state.incident_id}"
        key = self._make_key(tid)
        expire_time = ttl if ttl is not None else self.ttl

        state_dict = state.model_dump()
        success = self.client.set(key, state_dict, ex=expire_time)

        # Also store secondary key by incident_id for lookup
        if state.incident_id:
            sec_key = self._make_sec_key(state.incident_id)
            self.client.set(sec_key, tid, ex=expire_time)

        app_logger.info(f"[RedisWorkflowStore] Saved workflow state for thread '{tid}' (Incident: {state.incident_id}, TTL: {expire_time}s).")
        return success

    def load_workflow_state(self, identifier: str) -> Optional[EmergencyResponseState]:
        """
        Loads EmergencyResponseState from Redis using thread_id or incident_id.
        """
        # Try direct key by thread_id
        key = self._make_key(identifier)
        raw_json = self.client.get(key)

        # If not found, check secondary lookup key by incident_id
        if not raw_json:
            sec_key = self._make_sec_key(identifier)
            tid = self.client.get(sec_key)
            if tid:
                if isinstance(tid, str) and (tid.startswith("{") or tid.startswith('"')):
                    try:
                        tid = json.loads(tid)
                    except Exception:
                        pass
                raw_json = self.client.get(self._make_key(str(tid)))

        if not raw_json:
            app_logger.warning(f"[RedisWorkflowStore] Workflow state for '{identifier}' not found.")
            return None

        try:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            return EmergencyResponseState(**data)
        except Exception as e:
            app_logger.error(f"[RedisWorkflowStore] Error parsing workflow state JSON: {e}")
            return None

    def get_workflow_ttl(self, identifier: str) -> int:
        """Returns remaining TTL in seconds for a workflow state."""
        key = self._make_key(identifier)
        ttl_val = self.client.ttl(key)
        if ttl_val == -2:  # Check secondary key
            sec_key = self._make_sec_key(identifier)
            tid = self.client.get(sec_key)
            if tid:
                ttl_val = self.client.ttl(self._make_key(str(tid)))
        return ttl_val

    def extend_workflow_ttl(self, identifier: str, seconds: Optional[int] = None) -> bool:
        """Renews or extends TTL for workflow state."""
        expire_time = seconds or self.ttl
        key = self._make_key(identifier)
        res = self.client.expire(key, expire_time)
        sec_key = self._make_sec_key(identifier)
        if self.client.exists(sec_key):
            self.client.expire(sec_key, expire_time)
        return res

    def recover_workflow_state(self, identifier: str) -> Optional[EmergencyResponseState]:
        """
        Recovers interrupted or crashed workflow state from Redis.
        Re-attaches recovery flags if state was disrupted.
        """
        state = self.load_workflow_state(identifier)
        if state is None:
            return None

        if state.status not in ["COMPLETED", "FAILED"]:
            app_logger.warning(f"[RedisWorkflowStore] Recovering interrupted workflow '{identifier}' (Last stage: {state.execution_stage}).")
            state.recovery_triggered = True
            state.status = "RECOVERED"
            self.save_workflow_state(state, thread_id=identifier)

        return state

    def create_checkpoint(
        self,
        thread_id: str,
        checkpoint_name: str,
        state: EmergencyResponseState,
        ttl: Optional[int] = None
    ) -> str:
        """
        Creates a versioned snapshot checkpoint of the workflow state.
        """
        checkpoint_id = f"chk-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
        key = self._make_checkpoint_key(thread_id, checkpoint_id)
        index_key = self._make_checkpoint_list_key(thread_id)
        expire_time = ttl or redis_config.checkpoint_ttl

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "checkpoint_name": checkpoint_name,
            "timestamp": time.time(),
            "thread_id": thread_id,
            "state": state.model_dump()
        }

        self.client.set(key, checkpoint_data, ex=expire_time)
        self.client.rpush(index_key, checkpoint_id)
        self.client.expire(index_key, expire_time)

        app_logger.info(f"[RedisWorkflowStore] Created checkpoint '{checkpoint_id}' ({checkpoint_name}) for thread '{thread_id}'.")
        return checkpoint_id

    def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        """Lists metadata for all stored checkpoints of a thread."""
        index_key = self._make_checkpoint_list_key(thread_id)
        chk_ids = self.client.lrange(index_key, 0, -1)
        checkpoints = []
        for cid in chk_ids:
            key = self._make_checkpoint_key(thread_id, cid)
            raw = self.client.get(key)
            if raw:
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    checkpoints.append({
                        "checkpoint_id": data.get("checkpoint_id"),
                        "checkpoint_name": data.get("checkpoint_name"),
                        "timestamp": data.get("timestamp")
                    })
                except Exception:
                    pass
        return checkpoints

    def restore_checkpoint(self, thread_id: str, checkpoint_id: str) -> Optional[EmergencyResponseState]:
        """Restores workflow state from a specific checkpoint."""
        key = self._make_checkpoint_key(thread_id, checkpoint_id)
        raw = self.client.get(key)
        if not raw:
            app_logger.warning(f"[RedisWorkflowStore] Checkpoint '{checkpoint_id}' not found for thread '{thread_id}'.")
            return None

        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            state_data = data.get("state", {})
            state = EmergencyResponseState(**state_data)
            self.save_workflow_state(state, thread_id=thread_id)
            app_logger.info(f"[RedisWorkflowStore] Restored workflow '{thread_id}' from checkpoint '{checkpoint_id}'.")
            return state
        except Exception as e:
            app_logger.error(f"[RedisWorkflowStore] Failed to restore checkpoint '{checkpoint_id}': {e}")
            return None

    def delete_workflow_state(self, identifier: str) -> bool:
        """Deletes workflow state and related metadata from Redis."""
        key = self._make_key(identifier)
        sec_key = self._make_sec_key(identifier)
        deleted = self.client.delete(key) > 0
        self.client.delete(sec_key)
        return deleted


# Global Singleton Store
workflow_store = RedisWorkflowStore()
