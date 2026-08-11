"""
Redis Agent Memory Store

Manages short-term rolling conversation buffers and long-term key-value context memory
for AI agents in the Emergency Response System with TTL auto-expiration.
"""

import time
import json
from typing import Optional, Dict, Any, List
from memory.redis_client import redis_client, RedisClient
from memory.config import redis_config
from utils.logger import app_logger


class RedisAgentMemoryStore:
    """Manages rolling message history and persistent working context for AI Agents."""

    def __init__(self, client: Optional[RedisClient] = None):
        self.client = client or redis_client
        self.ttl = redis_config.agent_memory_ttl
        self.max_messages = redis_config.max_agent_memory_messages
        self.prefix = redis_config.agent_prefix

    def _make_memory_key(self, agent_id: str) -> str:
        return f"{self.prefix}messages:{agent_id}"

    def _make_context_key(self, agent_id: str) -> str:
        return f"{self.prefix}context:{agent_id}"

    def add_message(
        self,
        agent_id: str,
        role: str,
        content: str,
        max_messages: Optional[int] = None,
        ttl: Optional[int] = None
    ) -> int:
        """
        Appends interaction message to agent's rolling memory list.
        Truncates automatically if buffer exceeds limit.
        """
        key = self._make_memory_key(agent_id)
        limit = max_messages or self.max_messages
        expire_time = ttl if ttl is not None else self.ttl

        message = {
            "role": role,
            "content": content,
            "timestamp": time.time()
        }

        # Push right
        self.client.rpush(key, message)

        # Enforce rolling window
        current_len = self.client.llen(key)
        if current_len > limit:
            excess = current_len - limit
            for _ in range(excess):
                self.client.lpop(key)

        self.client.expire(key, expire_time)
        return min(current_len, limit)

    def get_memory(self, agent_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves rolling memory messages for an agent."""
        key = self._make_memory_key(agent_id)
        raw_list = self.client.lrange(key, 0, -1)
        messages = []
        for item in raw_list:
            try:
                messages.append(json.loads(item) if isinstance(item, str) else item)
            except Exception:
                pass

        if limit and limit > 0:
            messages = messages[-limit:]
        return messages

    def clear_memory(self, agent_id: str) -> bool:
        """Clears memory message history for an agent."""
        key = self._make_memory_key(agent_id)
        return self.client.delete(key) > 0

    # --- Agent Working Context (Hashes) ---
    def set_context_variable(
        self,
        agent_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Sets a key-value pair in agent's context store."""
        context_key = self._make_context_key(agent_id)
        expire_time = ttl if ttl is not None else self.ttl

        self.client.hset(context_key, key, value)
        self.client.expire(context_key, expire_time)
        return True

    def get_context_variable(self, agent_id: str, key: str) -> Optional[Any]:
        """Gets a context variable value for an agent."""
        context_key = self._make_context_key(agent_id)
        raw = self.client.hget(context_key, key)
        if raw is None:
            return None
        try:
            return json.loads(raw) if (raw.startswith("{") or raw.startswith("[")) else raw
        except Exception:
            return raw

    def get_all_context(self, agent_id: str) -> Dict[str, Any]:
        """Retrieves all working context variables for an agent."""
        context_key = self._make_context_key(agent_id)
        raw_dict = self.client.hgetall(context_key)
        parsed = {}
        for k, v in raw_dict.items():
            try:
                parsed[k] = json.loads(v) if (v.startswith("{") or v.startswith("[")) else v
            except Exception:
                parsed[k] = v
        return parsed

    def delete_context_variable(self, agent_id: str, key: str) -> bool:
        """Deletes a context variable from agent's store."""
        context_key = self._make_context_key(agent_id)
        return self.client.hdel(context_key, key) > 0

    def clear_all_context(self, agent_id: str) -> bool:
        """Deletes entire context store for an agent."""
        context_key = self._make_context_key(agent_id)
        return self.client.delete(context_key) > 0

    def get_agent_memory_ttl(self, agent_id: str) -> int:
        """Returns remaining TTL in seconds for an agent's memory keys."""
        key = self._make_memory_key(agent_id)
        return self.client.ttl(key)

    def extend_agent_memory_ttl(self, agent_id: str, seconds: Optional[int] = None) -> bool:
        """Extends TTL expiration for agent memory list and context hash."""
        expire_time = seconds or self.ttl
        mem_key = self._make_memory_key(agent_id)
        ctx_key = self._make_context_key(agent_id)
        res = self.client.expire(mem_key, expire_time)
        if self.client.exists(ctx_key):
            self.client.expire(ctx_key, expire_time)
        return res

    def sync_base_agent_memory(self, agent_instance: Any) -> bool:
        """
        Synchronizes a BaseAgent instance's memory_buffer with Redis memory.
        Loads existing messages into memory_buffer.
        """
        if not hasattr(agent_instance, "name"):
            return False

        agent_id = agent_instance.name
        existing_msgs = self.get_memory(agent_id, limit=10)
        if existing_msgs:
            agent_instance.memory_buffer = existing_msgs
            app_logger.info(f"[RedisAgentMemoryStore] Synced {len(existing_msgs)} messages for BaseAgent '{agent_id}'.")
        return True


# Global Singleton Store
agent_memory_store = RedisAgentMemoryStore()
