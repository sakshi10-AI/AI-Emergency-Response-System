"""
Unified State Checkpoint & Recovery Manager

Provides cross-domain state snapshot creation, listing, restoration, and retention
pruning across workflows, incidents, agent context, and system state.
"""

import time
import json
import uuid
from typing import Optional, Dict, Any, List
from memory.redis_client import redis_client, RedisClient
from memory.config import redis_config
from utils.logger import app_logger


class StateCheckpointManager:
    """Unified checkpoint manager for capturing and restoring state snapshots."""

    def __init__(self, client: Optional[RedisClient] = None):
        self.client = client or redis_client
        self.ttl = redis_config.checkpoint_ttl
        self.prefix = redis_config.checkpoint_prefix
        self.max_checkpoints = redis_config.max_checkpoints_per_entity

    def _make_key(self, domain: str, entity_id: str, checkpoint_id: str) -> str:
        return f"{self.prefix}{domain}:{entity_id}:{checkpoint_id}"

    def _make_index_key(self, domain: str, entity_id: str) -> str:
        return f"{self.prefix}{domain}:index:{entity_id}"

    def create_checkpoint(
        self,
        domain: str,
        entity_id: str,
        label: str,
        state_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> str:
        """
        Creates a time-stamped state checkpoint for a given domain and entity_id.
        Automatically prunes oldest checkpoints if max limit is reached.
        """
        checkpoint_id = f"chk-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
        key = self._make_key(domain, entity_id, checkpoint_id)
        index_key = self._make_index_key(domain, entity_id)
        expire_time = ttl if ttl is not None else self.ttl

        snapshot = {
            "checkpoint_id": checkpoint_id,
            "domain": domain,
            "entity_id": entity_id,
            "label": label,
            "timestamp": time.time(),
            "state_data": state_data
        }

        # Store checkpoint data
        self.client.set(key, snapshot, ex=expire_time)

        # Append checkpoint_id to index list
        self.client.rpush(index_key, checkpoint_id)
        self.client.expire(index_key, expire_time)

        # Enforce max retention
        self.prune_checkpoints(domain, entity_id)

        app_logger.info(f"[StateCheckpointManager] Created checkpoint '{checkpoint_id}' ({label}) for [{domain}] entity '{entity_id}'.")
        return checkpoint_id

    def get_checkpoint(
        self,
        domain: str,
        entity_id: str,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieves raw checkpoint snapshot dictionary."""
        key = self._make_key(domain, entity_id, checkpoint_id)
        raw = self.client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            app_logger.error(f"[StateCheckpointManager] Error parsing checkpoint '{checkpoint_id}': {e}")
            return None

    def list_checkpoints(self, domain: str, entity_id: str) -> List[Dict[str, Any]]:
        """Lists metadata of all checkpoints for an entity."""
        index_key = self._make_index_key(domain, entity_id)
        chk_ids = self.client.lrange(index_key, 0, -1)
        checkpoints = []
        for cid in chk_ids:
            chk = self.get_checkpoint(domain, entity_id, cid)
            if chk:
                checkpoints.append({
                    "checkpoint_id": chk.get("checkpoint_id"),
                    "domain": chk.get("domain"),
                    "entity_id": chk.get("entity_id"),
                    "label": chk.get("label"),
                    "timestamp": chk.get("timestamp")
                })
        return checkpoints

    def restore_latest_checkpoint(self, domain: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Restores the most recently created checkpoint for an entity."""
        index_key = self._make_index_key(domain, entity_id)
        latest_cid = self.client.rpop(index_key)
        if not latest_cid:
            return None

        # Re-push so list is preserved
        self.client.rpush(index_key, latest_cid)
        chk = self.get_checkpoint(domain, entity_id, latest_cid)
        if chk:
            app_logger.info(f"[StateCheckpointManager] Restored latest checkpoint '{latest_cid}' for [{domain}] entity '{entity_id}'.")
            return chk.get("state_data")
        return None

    def prune_checkpoints(
        self,
        domain: str,
        entity_id: str,
        keep_last: Optional[int] = None
    ) -> int:
        """Prunes oldest checkpoints keeping only the last N items."""
        keep_count = keep_last or self.max_checkpoints
        index_key = self._make_index_key(domain, entity_id)
        current_len = self.client.llen(index_key)
        pruned = 0

        if current_len > keep_count:
            excess = current_len - keep_count
            for _ in range(excess):
                oldest_cid = self.client.lpop(index_key)
                if oldest_cid:
                    old_key = self._make_key(domain, entity_id, oldest_cid)
                    self.client.delete(old_key)
                    pruned += 1

        return pruned


# Global Singleton Manager
checkpoint_manager = StateCheckpointManager()
