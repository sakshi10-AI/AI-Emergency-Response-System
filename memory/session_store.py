"""
Redis User/Dispatcher Session Memory Store

Manages dispatcher and user authentication sessions, active workspace contexts,
session TTL extensions on request activity, and attached incident tracking.
"""

import time
import json
from typing import Optional, Dict, Any, List, Set
from memory.redis_client import redis_client, RedisClient
from memory.config import redis_config
from utils.logger import app_logger


class RedisSessionStore:
    """Manages user/dispatcher active sessions in Redis."""

    def __init__(self, client: Optional[RedisClient] = None):
        self.client = client or redis_client
        self.ttl = redis_config.session_ttl
        self.prefix = redis_config.session_prefix

    def _make_session_key(self, session_id: str) -> str:
        return f"{self.prefix}id:{session_id}"

    def _make_user_index_key(self, user_id: str) -> str:
        return f"{self.prefix}user:{user_id}"

    def _make_incident_set_key(self, session_id: str) -> str:
        return f"{self.prefix}incidents:{session_id}"

    def create_session(
        self,
        session_id: str,
        user_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Creates a new active user/dispatcher session with TTL."""
        key = self._make_session_key(session_id)
        expire_time = ttl if ttl is not None else self.ttl

        session_payload = dict(user_data)
        session_payload["session_id"] = session_id
        session_payload["created_at"] = time.time()
        session_payload["last_active"] = time.time()

        user_id = session_payload.get("user_id")

        success = self.client.set(key, session_payload, ex=expire_time)

        # Reverse lookup mapping: user_id -> session_id
        if user_id:
            user_key = self._make_user_index_key(str(user_id))
            self.client.set(user_key, session_id, ex=expire_time)

        app_logger.info(f"[RedisSessionStore] Created session '{session_id}' for user '{user_id}' (TTL: {expire_time}s).")
        return success

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session payload from Redis."""
        key = self._make_session_key(session_id)
        raw = self.client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            app_logger.error(f"[RedisSessionStore] Error parsing session '{session_id}': {e}")
            return None

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Updates session fields and refreshes last_active timestamp."""
        session = self.get_session(session_id)
        if not session:
            return False

        session.update(updates)
        session["last_active"] = time.time()
        return self.create_session(session_id, session)

    def touch_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Refreshes TTL and last_active timestamp upon user request activity."""
        session = self.get_session(session_id)
        if not session:
            return False

        expire_time = ttl if ttl is not None else self.ttl
        session["last_active"] = time.time()
        key = self._make_session_key(session_id)
        self.client.set(key, session, ex=expire_time)

        user_id = session.get("user_id")
        if user_id:
            user_key = self._make_user_index_key(str(user_id))
            self.client.expire(user_key, expire_time)

        inc_key = self._make_incident_set_key(session_id)
        if self.client.exists(inc_key):
            self.client.expire(inc_key, expire_time)

        return True

    def get_session_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Finds session by user_id via index key."""
        user_key = self._make_user_index_key(str(user_id))
        sid = self.client.get(user_key)
        if sid:
            if isinstance(sid, str) and (sid.startswith('"') or sid.startswith('{')):
                try:
                    sid = json.loads(sid)
                except Exception:
                    pass
            return self.get_session(str(sid))
        return None

    def attach_incident_to_session(self, session_id: str, incident_id: str) -> bool:
        """Attaches an active incident ID to the dispatcher session."""
        inc_key = self._make_incident_set_key(session_id)
        self.client.sadd(inc_key, incident_id)
        self.client.expire(inc_key, self.ttl)
        return True

    def detach_incident_from_session(self, session_id: str, incident_id: str) -> bool:
        """Detaches an incident ID from the session."""
        inc_key = self._make_incident_set_key(session_id)
        return self.client.srem(inc_key, incident_id) > 0

    def get_session_incidents(self, session_id: str) -> Set[str]:
        """Returns set of active incident IDs attached to session."""
        inc_key = self._make_incident_set_key(session_id)
        return self.client.smembers(inc_key)

    def get_session_ttl(self, session_id: str) -> int:
        """Returns remaining TTL seconds for a session."""
        key = self._make_session_key(session_id)
        return self.client.ttl(key)

    def delete_session(self, session_id: str) -> bool:
        """Invalidates and deletes session, user index, and attached incident tracking."""
        session = self.get_session(session_id)
        if session and "user_id" in session:
            user_key = self._make_user_index_key(str(session["user_id"]))
            self.client.delete(user_key)

        key = self._make_session_key(session_id)
        inc_key = self._make_incident_set_key(session_id)
        deleted = self.client.delete(key) > 0
        self.client.delete(inc_key)
        app_logger.info(f"[RedisSessionStore] Deleted session '{session_id}'.")
        return deleted


# Global Singleton Store
session_store = RedisSessionStore()
