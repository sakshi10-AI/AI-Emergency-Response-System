"""
Redis Task Queue & Dead-Letter Queue Manager

Provides resilient FIFO message queueing, task state tracking (PENDING, PROCESSING,
COMPLETED, FAILED), Dead-Letter Queueing (DLQ), stuck task recovery, and TTL management.
"""

import time
import json
from typing import Optional, Dict, Any, List
from memory.redis_client import redis_client, RedisClient
from memory.config import redis_config
from utils.logger import app_logger


class RedisTaskQueue:
    """Manages asynchronous task queues, DLQ, task status, and recovery in Redis."""

    def __init__(self, client: Optional[RedisClient] = None):
        self.client = client or redis_client
        self.ttl = redis_config.task_queue_ttl
        self.prefix = redis_config.task_queue_prefix

    def _make_queue_key(self, queue_name: str) -> str:
        return f"{self.prefix}queue:{queue_name}"

    def _make_status_key(self, task_id: str) -> str:
        return f"{self.prefix}status:{task_id}"

    def _make_dlq_key(self, queue_name: str) -> str:
        return f"{self.prefix}dlq:{queue_name}"

    def enqueue_task(
        self,
        queue_name: str,
        task_id: str,
        payload: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Enqueues task payload to queue list and sets status to PENDING."""
        queue_key = self._make_queue_key(queue_name)
        status_key = self._make_status_key(task_id)
        expire_time = ttl if ttl is not None else self.ttl

        task_item = {
            "task_id": task_id,
            "queue_name": queue_name,
            "payload": payload,
            "enqueued_at": time.time(),
            "attempts": 0
        }

        status_info = {
            "task_id": task_id,
            "queue_name": queue_name,
            "status": "PENDING",
            "enqueued_at": time.time(),
            "result": None,
            "error": None
        }

        # Save status object with TTL
        self.client.set(status_key, status_info, ex=expire_time)

        # Push payload left into queue list
        self.client.lpush(queue_key, task_item)
        self.client.expire(queue_key, expire_time)

        app_logger.info(f"[RedisTaskQueue] Enqueued task '{task_id}' into queue '{queue_name}'.")
        return True

    def dequeue_task(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Pops task from right of queue list (FIFO) and transitions status to PROCESSING.
        """
        queue_key = self._make_queue_key(queue_name)
        raw_item = self.client.rpop(queue_key)
        if not raw_item:
            return None

        try:
            item = json.loads(raw_item) if isinstance(raw_item, str) else raw_item
            task_id = item.get("task_id")
            item["attempts"] = item.get("attempts", 0) + 1
            item["dequeued_at"] = time.time()

            # Update status to PROCESSING
            if task_id:
                self.update_task_status(task_id, "PROCESSING", metadata={"started_at": time.time(), "attempts": item["attempts"]})

            return item
        except Exception as e:
            app_logger.error(f"[RedisTaskQueue] Error parsing dequeued task: {e}")
            return None

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Updates task execution status in Redis (PENDING, PROCESSING, COMPLETED, FAILED, DLQ)."""
        status_key = self._make_status_key(task_id)
        current = self.get_task_status(task_id) or {"task_id": task_id, "status": "UNKNOWN"}
        expire_time = ttl if ttl is not None else self.ttl

        current["status"] = status
        current["updated_at"] = time.time()
        if result is not None:
            current["result"] = result
        if error is not None:
            current["error"] = error
        if metadata:
            current.update(metadata)

        return self.client.set(status_key, current, ex=expire_time)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Gets current task status dictionary from Redis."""
        status_key = self._make_status_key(task_id)
        raw = self.client.get(status_key)
        if not raw:
            return None
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return None

    def move_to_dlq(
        self,
        queue_name: str,
        task_id: str,
        payload: Dict[str, Any],
        error_reason: str
    ) -> bool:
        """Moves a failed or unrecoverable task into the Dead-Letter Queue (DLQ)."""
        dlq_key = self._make_dlq_key(queue_name)
        dlq_item = {
            "task_id": task_id,
            "queue_name": queue_name,
            "payload": payload,
            "failed_at": time.time(),
            "error_reason": error_reason
        }

        self.client.lpush(dlq_key, dlq_item)
        self.client.expire(dlq_key, self.ttl)
        self.update_task_status(task_id, "FAILED", error=error_reason, metadata={"moved_to_dlq": True})

        app_logger.warning(f"[RedisTaskQueue] Task '{task_id}' moved to DLQ for queue '{queue_name}' (Reason: {error_reason}).")
        return True

    def get_dlq_tasks(self, queue_name: str) -> List[Dict[str, Any]]:
        """Retrieves list of tasks in Dead-Letter Queue."""
        dlq_key = self._make_dlq_key(queue_name)
        raw_list = self.client.lrange(dlq_key, 0, -1)
        dlq_tasks = []
        for item in raw_list:
            try:
                dlq_tasks.append(json.loads(item) if isinstance(item, str) else item)
            except Exception:
                pass
        return dlq_tasks

    def get_queue_length(self, queue_name: str) -> int:
        """Returns pending task count in queue."""
        queue_key = self._make_queue_key(queue_name)
        return self.client.llen(queue_key)

    def get_task_ttl(self, task_id: str) -> int:
        """Returns remaining TTL seconds for a task status record."""
        status_key = self._make_status_key(task_id)
        return self.client.ttl(status_key)

    def recover_stuck_tasks(
        self,
        queue_name: str,
        max_processing_age_seconds: float = 300.0
    ) -> int:
        """
        Scans tasks in PROCESSING status older than threshold and resets them to PENDING or DLQ.
        """
        pattern = f"{self.prefix}status:*"
        keys = self.client.keys(pattern)
        recovered_count = 0
        now = time.time()

        for k in keys:
            raw = self.client.get(k)
            if not raw:
                continue
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                if data.get("queue_name") == queue_name and data.get("status") == "PROCESSING":
                    started_at = data.get("started_at", data.get("updated_at", 0))
                    if now - started_at > max_processing_age_seconds:
                        task_id = data.get("task_id")
                        attempts = data.get("attempts", 1)
                        if attempts >= 3:
                            self.move_to_dlq(queue_name, task_id, data, "Max retries exceeded during crash recovery")
                        else:
                            self.update_task_status(task_id, "PENDING", metadata={"recovery_reset": True})
                            # Re-enqueue
                            self.enqueue_task(queue_name, task_id, data.get("payload", {}))
                        recovered_count += 1
            except Exception as e:
                app_logger.error(f"[RedisTaskQueue] Error recovering stuck task key '{k}': {e}")

        if recovered_count > 0:
            app_logger.info(f"[RedisTaskQueue] Recovered {recovered_count} stuck tasks in queue '{queue_name}'.")
        return recovered_count

    def clear_queue(self, queue_name: str) -> bool:
        """Clears all pending items from queue."""
        queue_key = self._make_queue_key(queue_name)
        dlq_key = self._make_dlq_key(queue_name)
        self.client.delete(queue_key)
        self.client.delete(dlq_key)
        return True


# Global Singleton Store
task_queue = RedisTaskQueue()
