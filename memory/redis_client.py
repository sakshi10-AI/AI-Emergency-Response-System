"""
Redis Client Manager & Resilient Fallback Storage

Manages connection pooling for Redis operations.
Features automatic fallback to an in-memory resilient dictionary if the Redis server
is unavailable or unreachable, ensuring zero application runtime crashes.
"""

import time
import json
from typing import Any, Optional, Dict, List, Set, Union
from memory.config import redis_config, RedisMemoryConfig
from utils.logger import app_logger

# Try importing redis
try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ResilientInMemoryStorage:
    """In-memory dictionary fallback store mimicking Redis data structures."""

    def __init__(self):
        self._kv: Dict[str, Any] = {}
        self._expirations: Dict[str, float] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._hashes: Dict[str, Dict[str, Any]] = {}
        self._sets: Dict[str, Set[Any]] = {}

    def _purge_expired(self, key: str):
        if key in self._expirations and time.time() > self._expirations[key]:
            self._kv.pop(key, None)
            self._expirations.pop(key, None)
            self._lists.pop(key, None)
            self._hashes.pop(key, None)
            self._sets.pop(key, None)

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> Optional[str]:
        self._purge_expired(key)
        val = self._kv.get(key)
        if val is None:
            return None
        return json.dumps(val) if isinstance(val, (dict, list)) else str(val)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._kv[key] = value
        if ex:
            self._expirations[key] = time.time() + ex
        else:
            self._expirations.pop(key, None)
        return True

    def delete(self, key: str) -> int:
        existed = key in self._kv or key in self._lists or key in self._hashes or key in self._sets
        self._kv.pop(key, None)
        self._expirations.pop(key, None)
        self._lists.pop(key, None)
        self._hashes.pop(key, None)
        self._sets.pop(key, None)
        return 1 if existed else 0

    def expire(self, key: str, seconds: int) -> bool:
        self._purge_expired(key)
        if key in self._kv or key in self._lists or key in self._hashes or key in self._sets:
            self._expirations[key] = time.time() + seconds
            return True
        return False

    def ttl(self, key: str) -> int:
        self._purge_expired(key)
        if key not in self._kv and key not in self._lists and key not in self._hashes and key not in self._sets:
            return -2
        if key not in self._expirations:
            return -1
        rem = int(self._expirations[key] - time.time())
        return rem if rem >= 0 else -2

    def exists(self, key: str) -> int:
        self._purge_expired(key)
        existed = key in self._kv or key in self._lists or key in self._hashes or key in self._sets
        return 1 if existed else 0

    def keys(self, pattern: str = "*") -> List[str]:
        valid_keys = []
        all_keys = list(self._kv.keys()) + list(self._lists.keys()) + list(self._hashes.keys()) + list(self._sets.keys())
        for k in set(all_keys):
            self._purge_expired(k)
            if k in self._kv or k in self._lists or k in self._hashes or k in self._sets:
                if pattern == "*":
                    valid_keys.append(k)
                else:
                    sub = pattern.replace("*", "")
                    if sub in k:
                        valid_keys.append(k)
        return valid_keys

    # --- List Operations ---
    def lpush(self, key: str, *values: Any) -> int:
        self._purge_expired(key)
        if key not in self._lists:
            self._lists[key] = []
        for v in values:
            self._lists[key].insert(0, str(v) if not isinstance(v, str) else v)
        return len(self._lists[key])

    def rpush(self, key: str, *values: Any) -> int:
        self._purge_expired(key)
        if key not in self._lists:
            self._lists[key] = []
        for v in values:
            self._lists[key].append(str(v) if not isinstance(v, str) else v)
        return len(self._lists[key])

    def lpop(self, key: str) -> Optional[str]:
        self._purge_expired(key)
        if key in self._lists and self._lists[key]:
            return self._lists[key].pop(0)
        return None

    def rpop(self, key: str) -> Optional[str]:
        self._purge_expired(key)
        if key in self._lists and self._lists[key]:
            return self._lists[key].pop()
        return None

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        self._purge_expired(key)
        lst = self._lists.get(key, [])
        if not lst:
            return []
        if end == -1:
            return lst[start:]
        return lst[start:end+1]

    def llen(self, key: str) -> int:
        self._purge_expired(key)
        return len(self._lists.get(key, []))

    def lrem(self, key: str, count: int, value: Any) -> int:
        self._purge_expired(key)
        if key not in self._lists:
            return 0
        target = str(value) if not isinstance(value, str) else value
        lst = self._lists[key]
        removed = 0
        if count == 0:
            new_lst = [x for x in lst if x != target]
            removed = len(lst) - len(new_lst)
            self._lists[key] = new_lst
        elif count > 0:
            new_lst = []
            for item in lst:
                if item == target and removed < count:
                    removed += 1
                else:
                    new_lst.append(item)
            self._lists[key] = new_lst
        return removed

    # --- Hash Operations ---
    def hset(self, key: str, field: str, value: Any) -> int:
        self._purge_expired(key)
        if key not in self._hashes:
            self._hashes[key] = {}
        val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        is_new = field not in self._hashes[key]
        self._hashes[key][field] = val_str
        return 1 if is_new else 0

    def hget(self, key: str, field: str) -> Optional[str]:
        self._purge_expired(key)
        if key in self._hashes:
            return self._hashes[key].get(field)
        return None

    def hgetall(self, key: str) -> Dict[str, str]:
        self._purge_expired(key)
        return dict(self._hashes.get(key, {}))

    def hdel(self, key: str, *fields: str) -> int:
        self._purge_expired(key)
        if key not in self._hashes:
            return 0
        count = 0
        for f in fields:
            if f in self._hashes[key]:
                del self._hashes[key][f]
                count += 1
        return count

    def hexists(self, key: str, field: str) -> bool:
        self._purge_expired(key)
        return field in self._hashes.get(key, {})

    # --- Set Operations ---
    def sadd(self, key: str, *values: Any) -> int:
        self._purge_expired(key)
        if key not in self._sets:
            self._sets[key] = set()
        added = 0
        for v in values:
            val_str = str(v) if not isinstance(v, str) else v
            if val_str not in self._sets[key]:
                self._sets[key].add(val_str)
                added += 1
        return added

    def smembers(self, key: str) -> Set[str]:
        self._purge_expired(key)
        return set(self._sets.get(key, set()))

    def srem(self, key: str, *values: Any) -> int:
        self._purge_expired(key)
        if key not in self._sets:
            return 0
        removed = 0
        for v in values:
            val_str = str(v) if not isinstance(v, str) else v
            if val_str in self._sets[key]:
                self._sets[key].remove(val_str)
                removed += 1
        return removed

    def sismember(self, key: str, value: Any) -> bool:
        self._purge_expired(key)
        val_str = str(value) if not isinstance(value, str) else value
        return val_str in self._sets.get(key, set())


class RedisClient:
    """
    Centralized Redis Client manager.
    Handles connections to Redis with fallback to ResilientInMemoryStorage.
    """

    _instance: Optional["RedisClient"] = None

    def __init__(self, config: Optional[RedisMemoryConfig] = None):
        self.config = config or redis_config
        self.sync_client: Optional[Any] = None
        self.fallback_storage = ResilientInMemoryStorage()
        self.is_connected = False

        self._init_connection()

    @classmethod
    def get_instance(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = RedisClient()
        return cls._instance

    def _init_connection(self):
        if not REDIS_AVAILABLE:
            app_logger.warning("[RedisClient] 'redis' library not installed. Running in resilient in-memory mode.")
            self.is_connected = False
            return

        try:
            self.sync_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                socket_timeout=self.config.socket_timeout,
                decode_responses=True
            )
            # Ping test
            self.sync_client.ping()
            self.is_connected = True
            app_logger.info(f"[RedisClient] Connected to Redis at {self.config.redis_host}:{self.config.redis_port} (DB {self.config.redis_db}).")
        except Exception as e:
            app_logger.warning(f"[RedisClient] Redis server unreachable ({e}). Active resilient in-memory fallback storage.")
            self.is_connected = False
            self.sync_client = None

    def ping(self) -> bool:
        if self.is_connected and self.sync_client:
            try:
                return bool(self.sync_client.ping())
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis ping error: {e}. Using fallback.")
        return self.fallback_storage.ping()

    def get(self, key: str) -> Optional[str]:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.get(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis get error: {e}. Using fallback.")
        return self.fallback_storage.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value)
        else:
            val_str = str(value)

        if self.is_connected and self.sync_client:
            try:
                return bool(self.sync_client.set(key, val_str, ex=ex))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis set error: {e}. Using fallback.")

        return self.fallback_storage.set(key, val_str, ex=ex)

    def delete(self, key: str) -> int:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.delete(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis delete error: {e}. Using fallback.")
        return self.fallback_storage.delete(key)

    def expire(self, key: str, seconds: int) -> bool:
        if self.is_connected and self.sync_client:
            try:
                return bool(self.sync_client.expire(key, seconds))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis expire error: {e}. Using fallback.")
        return self.fallback_storage.expire(key, seconds)

    def ttl(self, key: str) -> int:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.ttl(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis ttl error: {e}. Using fallback.")
        return self.fallback_storage.ttl(key)

    def exists(self, key: str) -> int:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.exists(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis exists error: {e}. Using fallback.")
        return self.fallback_storage.exists(key)

    def keys(self, pattern: str = "*") -> List[str]:
        if self.is_connected and self.sync_client:
            try:
                return list(self.sync_client.keys(pattern))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis keys error: {e}. Using fallback.")
        return self.fallback_storage.keys(pattern)

    # --- List Operations ---
    def lpush(self, key: str, *values: Any) -> int:
        str_vals = [json.dumps(v) if isinstance(v, (dict, list)) else str(v) for v in values]
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.lpush(key, *str_vals)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis lpush error: {e}. Using fallback.")
        return self.fallback_storage.lpush(key, *str_vals)

    def rpush(self, key: str, *values: Any) -> int:
        str_vals = [json.dumps(v) if isinstance(v, (dict, list)) else str(v) for v in values]
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.rpush(key, *str_vals)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis rpush error: {e}. Using fallback.")
        return self.fallback_storage.rpush(key, *str_vals)

    def lpop(self, key: str) -> Optional[str]:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.lpop(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis lpop error: {e}. Using fallback.")
        return self.fallback_storage.lpop(key)

    def rpop(self, key: str) -> Optional[str]:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.rpop(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis rpop error: {e}. Using fallback.")
        return self.fallback_storage.rpop(key)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        if self.is_connected and self.sync_client:
            try:
                return list(self.sync_client.lrange(key, start, end))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis lrange error: {e}. Using fallback.")
        return self.fallback_storage.lrange(key, start, end)

    def llen(self, key: str) -> int:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.llen(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis llen error: {e}. Using fallback.")
        return self.fallback_storage.llen(key)

    def lrem(self, key: str, count: int, value: Any) -> int:
        val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.lrem(key, count, val_str)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis lrem error: {e}. Using fallback.")
        return self.fallback_storage.lrem(key, count, val_str)

    # --- Hash Operations ---
    def hset(self, key: str, field: str, value: Any) -> int:
        val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.hset(key, field, val_str)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis hset error: {e}. Using fallback.")
        return self.fallback_storage.hset(key, field, val_str)

    def hget(self, key: str, field: str) -> Optional[str]:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.hget(key, field)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis hget error: {e}. Using fallback.")
        return self.fallback_storage.hget(key, field)

    def hgetall(self, key: str) -> Dict[str, str]:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.hgetall(key)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis hgetall error: {e}. Using fallback.")
        return self.fallback_storage.hgetall(key)

    def hdel(self, key: str, *fields: str) -> int:
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.hdel(key, *fields)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis hdel error: {e}. Using fallback.")
        return self.fallback_storage.hdel(key, *fields)

    def hexists(self, key: str, field: str) -> bool:
        if self.is_connected and self.sync_client:
            try:
                return bool(self.sync_client.hexists(key, field))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis hexists error: {e}. Using fallback.")
        return self.fallback_storage.hexists(key, field)

    # --- Set Operations ---
    def sadd(self, key: str, *values: Any) -> int:
        str_vals = [json.dumps(v) if isinstance(v, (dict, list)) else str(v) for v in values]
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.sadd(key, *str_vals)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis sadd error: {e}. Using fallback.")
        return self.fallback_storage.sadd(key, *str_vals)

    def smembers(self, key: str) -> Set[str]:
        if self.is_connected and self.sync_client:
            try:
                return set(self.sync_client.smembers(key))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis smembers error: {e}. Using fallback.")
        return self.fallback_storage.smembers(key)

    def srem(self, key: str, *values: Any) -> int:
        str_vals = [json.dumps(v) if isinstance(v, (dict, list)) else str(v) for v in values]
        if self.is_connected and self.sync_client:
            try:
                return self.sync_client.srem(key, *str_vals)
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis srem error: {e}. Using fallback.")
        return self.fallback_storage.srem(key, *str_vals)

    def sismember(self, key: str, value: Any) -> bool:
        val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        if self.is_connected and self.sync_client:
            try:
                return bool(self.sync_client.sismember(key, val_str))
            except Exception as e:
                app_logger.error(f"[RedisClient] Redis sismember error: {e}. Using fallback.")
        return self.fallback_storage.sismember(key, val_str)


# Global Singleton Client
redis_client = RedisClient.get_instance()
