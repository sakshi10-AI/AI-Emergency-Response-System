"""
Redis Incident State Store & Recovery Manager

Saves, updates, and tracks active incident state, timeline events, state checkpoints,
and crash recovery using Redis.
"""

import time
import json
import uuid
from typing import Optional, Dict, Any, List
from memory.redis_client import redis_client, RedisClient
from memory.config import redis_config
from utils.logger import app_logger


class RedisIncidentStore:
    """Manages persistent incident states, timeline events, checkpoints, and recovery in Redis."""

    def __init__(self, client: Optional[RedisClient] = None):
        self.client = client or redis_client
        self.ttl = redis_config.incident_ttl
        self.prefix = redis_config.incident_prefix

    def _make_key(self, incident_id: str) -> str:
        return f"{self.prefix}state:{incident_id}"

    def _make_timeline_key(self, incident_id: str) -> str:
        return f"{self.prefix}timeline:{incident_id}"

    def _make_checkpoint_key(self, incident_id: str, checkpoint_id: str) -> str:
        return f"{redis_config.checkpoint_prefix}incident:{incident_id}:{checkpoint_id}"

    def _make_checkpoint_list_key(self, incident_id: str) -> str:
        return f"{redis_config.checkpoint_prefix}incident:index:{incident_id}"

    def save_incident(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Saves or updates incident state dict in Redis."""
        key = self._make_key(incident_id)
        expire_time = ttl if ttl is not None else self.ttl

        payload = dict(incident_data)
        payload["incident_id"] = incident_id
        if "updated_at" not in payload:
            payload["updated_at"] = time.time()
        if "created_at" not in payload:
            payload["created_at"] = time.time()

        success = self.client.set(key, payload, ex=expire_time)
        app_logger.info(f"[RedisIncidentStore] Saved incident state for '{incident_id}' (TTL: {expire_time}s).")
        return success

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves incident state dictionary from Redis."""
        key = self._make_key(incident_id)
        raw_json = self.client.get(key)
        if not raw_json:
            return None
        try:
            return json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except Exception as e:
            app_logger.error(f"[RedisIncidentStore] Failed parsing incident state '{incident_id}': {e}")
            return None

    def update_incident_status(
        self,
        incident_id: str,
        new_status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Updates status field and appends event to incident timeline."""
        data = self.get_incident(incident_id) or {"incident_id": incident_id, "created_at": time.time()}
        old_status = data.get("status", "UNKNOWN")
        data["status"] = new_status
        data["updated_at"] = time.time()
        if metadata:
            data.update(metadata)

        success = self.save_incident(incident_id, data)

        event = {
            "timestamp": time.time(),
            "event_type": "STATUS_CHANGE",
            "old_status": old_status,
            "new_status": new_status,
            "details": metadata or {}
        }
        self.add_timeline_event(incident_id, event)
        return success

    def add_timeline_event(self, incident_id: str, event: Dict[str, Any]) -> int:
        """Appends a timestamped event entry to the incident timeline."""
        timeline_key = self._make_timeline_key(incident_id)
        event_payload = dict(event)
        if "timestamp" not in event_payload:
            event_payload["timestamp"] = time.time()

        count = self.client.rpush(timeline_key, event_payload)
        self.client.expire(timeline_key, self.ttl)
        return count

    def get_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        """Returns full chronological timeline list of events for an incident."""
        timeline_key = self._make_timeline_key(incident_id)
        raw_list = self.client.lrange(timeline_key, 0, -1)
        events = []
        for item in raw_list:
            try:
                events.append(json.loads(item) if isinstance(item, str) else item)
            except Exception:
                pass
        return events

    def get_incident_ttl(self, incident_id: str) -> int:
        """Returns remaining TTL in seconds for an incident key."""
        key = self._make_key(incident_id)
        return self.client.ttl(key)

    def extend_incident_ttl(self, incident_id: str, seconds: Optional[int] = None) -> bool:
        """Extends or resets expiration TTL for an incident and its timeline."""
        expire_time = seconds or self.ttl
        key = self._make_key(incident_id)
        res = self.client.expire(key, expire_time)
        timeline_key = self._make_timeline_key(incident_id)
        if self.client.exists(timeline_key):
            self.client.expire(timeline_key, expire_time)
        return res

    def create_checkpoint(
        self,
        incident_id: str,
        snapshot_label: str,
        ttl: Optional[int] = None
    ) -> Optional[str]:
        """Creates a snapshot checkpoint of the current incident state."""
        current_data = self.get_incident(incident_id)
        if not current_data:
            return None

        checkpoint_id = f"chk-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
        key = self._make_checkpoint_key(incident_id, checkpoint_id)
        index_key = self._make_checkpoint_list_key(incident_id)
        expire_time = ttl or redis_config.checkpoint_ttl

        checkpoint_payload = {
            "checkpoint_id": checkpoint_id,
            "label": snapshot_label,
            "timestamp": time.time(),
            "incident_id": incident_id,
            "data": current_data
        }

        self.client.set(key, checkpoint_payload, ex=expire_time)
        self.client.rpush(index_key, checkpoint_id)
        self.client.expire(index_key, expire_time)

        app_logger.info(f"[RedisIncidentStore] Created checkpoint '{checkpoint_id}' ({snapshot_label}) for incident '{incident_id}'.")
        return checkpoint_id

    def list_checkpoints(self, incident_id: str) -> List[Dict[str, Any]]:
        """Lists metadata of stored checkpoints for an incident."""
        index_key = self._make_checkpoint_list_key(incident_id)
        chk_ids = self.client.lrange(index_key, 0, -1)
        checkpoints = []
        for cid in chk_ids:
            key = self._make_checkpoint_key(incident_id, cid)
            raw = self.client.get(key)
            if raw:
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    checkpoints.append({
                        "checkpoint_id": data.get("checkpoint_id"),
                        "label": data.get("label"),
                        "timestamp": data.get("timestamp")
                    })
                except Exception:
                    pass
        return checkpoints

    def restore_checkpoint(self, incident_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Restores incident state from a given checkpoint."""
        key = self._make_checkpoint_key(incident_id, checkpoint_id)
        raw = self.client.get(key)
        if not raw:
            return None

        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
            restored_data = payload.get("data", {})
            restored_data["restored_from_checkpoint"] = checkpoint_id
            restored_data["restored_at"] = time.time()
            self.save_incident(incident_id, restored_data)

            self.add_timeline_event(incident_id, {
                "event_type": "CHECKPOINT_RESTORED",
                "checkpoint_id": checkpoint_id,
                "label": payload.get("label")
            })

            app_logger.info(f"[RedisIncidentStore] Restored incident '{incident_id}' from checkpoint '{checkpoint_id}'.")
            return restored_data
        except Exception as e:
            app_logger.error(f"[RedisIncidentStore] Error restoring checkpoint '{checkpoint_id}': {e}")
            return None

    def recover_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Recovers an interrupted incident state, marking it RECOVERED."""
        incident = self.get_incident(incident_id)
        if not incident:
            return None

        if incident.get("status") not in ["RESOLVED", "CLOSED", "CANCELLED"]:
            incident["recovery_triggered"] = True
            incident["status"] = "RECOVERED"
            self.save_incident(incident_id, incident)
            self.add_timeline_event(incident_id, {
                "event_type": "INCIDENT_RECOVERY",
                "message": "Incident state recovered after disruption."
            })
            app_logger.warning(f"[RedisIncidentStore] Triggered recovery on active incident '{incident_id}'.")
        return incident

    def delete_incident(self, incident_id: str) -> bool:
        """Deletes incident state and timeline from Redis."""
        key = self._make_key(incident_id)
        timeline_key = self._make_timeline_key(incident_id)
        deleted = self.client.delete(key) > 0
        self.client.delete(timeline_key)
        return deleted


# Global Singleton Store
incident_store = RedisIncidentStore()
