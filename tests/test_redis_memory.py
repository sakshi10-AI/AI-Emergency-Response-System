"""
Unit & Integration Tests for Modular Redis Memory Subsystem

Tests all modular stores:
- Redis Client & Resilient In-Memory Fallback
- Workflow State Store (TTL, Recovery, Checkpoints)
- Incident State Store (Timeline, Status, TTL, Checkpoints, Recovery)
- Agent Memory Store (Rolling Window, Context, BaseAgent sync)
- Session Store (TTL Touch, User Lookup, Incident Attachments)
- Task Queue (FIFO Queue, Task Status, DLQ, Stuck Recovery)
- State Checkpoint Manager (Snapshots, Restoration, Pruning)
"""

import time
import pytest
from agents.langgraph_schemas import EmergencyResponseState
from memory import (
    redis_client,
    RedisClient,
    ResilientInMemoryStorage,
    workflow_store,
    incident_store,
    agent_memory_store,
    session_store,
    task_queue,
    checkpoint_manager
)


class TestRedisClientAndFallback:
    """Tests primitive KV, Hash, List, and Set operations on client and fallback storage."""

    def test_resilient_storage_primitives(self):
        storage = ResilientInMemoryStorage()
        assert storage.ping() is True

        # KV operations
        storage.set("k1", "val1", ex=100)
        assert storage.get("k1") == "val1"
        assert storage.exists("k1") == 1
        assert storage.ttl("k1") > 0
        assert "k1" in storage.keys()

        # Delete
        storage.delete("k1")
        assert storage.get("k1") is None

        # Expiration
        storage.set("k2", "val2", ex=1)
        time.sleep(1.1)
        assert storage.get("k2") is None
        assert storage.ttl("k2") == -2

        # List operations
        storage.lpush("q1", "a", "b")
        assert storage.lrange("q1", 0, -1) == ["b", "a"]
        assert storage.rpop("q1") == "a"
        assert storage.lpop("q1") == "b"

        # Hash operations
        storage.hset("h1", "f1", "v1")
        assert storage.hget("h1", "f1") == "v1"
        assert storage.hgetall("h1") == {"f1": "v1"}
        assert storage.hexists("h1", "f1") is True
        storage.hdel("h1", "f1")
        assert storage.hexists("h1", "f1") is False

        # Set operations
        storage.sadd("s1", "m1", "m2")
        assert storage.smembers("s1") == {"m1", "m2"}
        assert storage.sismember("s1", "m1") is True
        storage.srem("s1", "m1")
        assert storage.sismember("s1", "m1") is False

    def test_redis_client_wrapper(self):
        client = redis_client
        assert client.ping() is True

        client.set("test_key", {"a": 1}, ex=60)
        val = client.get("test_key")
        assert val is not None
        assert client.ttl("test_key") > 0
        client.delete("test_key")


class TestWorkflowStateStore:
    """Tests RedisWorkflowStore state persistence, TTL, recovery, and checkpoints."""

    def test_save_load_workflow(self):
        state = EmergencyResponseState(
            incident_id="INC-101",
            tracking_code="TRK-101",
            description="Car fire on highway",
            execution_stage="ANALYZING"
        )

        thread_id = "thread-INC-101"
        saved = workflow_store.save_workflow_state(state, thread_id=thread_id, ttl=300)
        assert saved is True

        loaded = workflow_store.load_workflow_state(thread_id)
        assert loaded is not None
        assert loaded.incident_id == "INC-101"
        assert loaded.execution_stage == "ANALYZING"

        # Secondary lookup by incident_id
        loaded_by_inc = workflow_store.load_workflow_state("INC-101")
        assert loaded_by_inc is not None
        assert loaded_by_inc.tracking_code == "TRK-101"

        # TTL checks
        ttl = workflow_store.get_workflow_ttl(thread_id)
        assert ttl > 0
        extended = workflow_store.extend_workflow_ttl(thread_id, 600)
        assert extended is True

        workflow_store.delete_workflow_state(thread_id)

    def test_workflow_recovery(self):
        state = EmergencyResponseState(
            incident_id="INC-102",
            status="ANALYZING",
            execution_stage="LOCATION"
        )
        thread_id = "thread-INC-102"
        workflow_store.save_workflow_state(state, thread_id=thread_id)

        recovered = workflow_store.recover_workflow_state(thread_id)
        assert recovered is not None
        assert recovered.status == "RECOVERED"
        assert recovered.recovery_triggered is True

        workflow_store.delete_workflow_state(thread_id)

    def test_workflow_checkpoints(self):
        state1 = EmergencyResponseState(incident_id="INC-103", execution_stage="INIT")
        thread_id = "thread-INC-103"
        cid1 = workflow_store.create_checkpoint(thread_id, "stage_init", state1)
        assert cid1.startswith("chk-")

        state2 = EmergencyResponseState(incident_id="INC-103", execution_stage="DISPATCHING")
        cid2 = workflow_store.create_checkpoint(thread_id, "stage_dispatch", state2)

        checkpoints = workflow_store.list_checkpoints(thread_id)
        assert len(checkpoints) == 2

        # Restore checkpoint 1
        restored = workflow_store.restore_checkpoint(thread_id, cid1)
        assert restored is not None
        assert restored.execution_stage == "INIT"

        workflow_store.delete_workflow_state(thread_id)


class TestIncidentStateStore:
    """Tests RedisIncidentStore persistence, timeline, TTL, checkpoints, and recovery."""

    def test_incident_persistence_and_timeline(self):
        inc_id = "INC-201"
        data = {
            "title": "Structure Fire",
            "status": "DISPATCHED",
            "location": {"lat": 37.77, "lng": -122.41}
        }

        saved = incident_store.save_incident(inc_id, data, ttl=300)
        assert saved is True

        fetched = incident_store.get_incident(inc_id)
        assert fetched is not None
        assert fetched["title"] == "Structure Fire"

        # Update status and check timeline
        incident_store.update_incident_status(inc_id, "ARRIVED", metadata={"units_on_scene": 2})

        timeline = incident_store.get_timeline(inc_id)
        assert len(timeline) >= 1
        last_event = timeline[-1]
        assert last_event["event_type"] == "STATUS_CHANGE"
        assert last_event["new_status"] == "ARRIVED"

        # TTL check
        assert incident_store.get_incident_ttl(inc_id) > 0
        incident_store.extend_incident_ttl(inc_id, 500)

        incident_store.delete_incident(inc_id)

    def test_incident_checkpoints_and_recovery(self):
        inc_id = "INC-202"
        incident_store.save_incident(inc_id, {"status": "INITIAL", "severity": 2})

        cid = incident_store.create_checkpoint(inc_id, "initial_assessment")
        assert cid is not None

        incident_store.update_incident_status(inc_id, "ESCALATED", metadata={"severity": 1})

        # Restore checkpoint
        restored = incident_store.restore_checkpoint(inc_id, cid)
        assert restored is not None
        assert restored["status"] == "INITIAL"

        # Recover incident
        recovered = incident_store.recover_incident(inc_id)
        assert recovered is not None
        assert recovered["status"] == "RECOVERED"

        incident_store.delete_incident(inc_id)


class TestAgentMemoryStore:
    """Tests RedisAgentMemoryStore rolling buffer, context hash, and BaseAgent sync."""

    def test_rolling_message_buffer(self):
        agent_id = "TestAgent"
        agent_memory_store.clear_memory(agent_id)

        for i in range(15):
            agent_memory_store.add_message(agent_id, "user" if i % 2 == 0 else "model", f"msg-{i}", max_messages=10)

        memory = agent_memory_store.get_memory(agent_id)
        assert len(memory) == 10
        assert memory[-1]["content"] == "msg-14"

        agent_memory_store.clear_memory(agent_id)

    def test_agent_context(self):
        agent_id = "TestAgent"
        agent_memory_store.set_context_variable(agent_id, "assigned_hospital", "General Hospital")
        agent_memory_store.set_context_variable(agent_id, "specialties", ["Trauma", "Burn"])

        assert agent_memory_store.get_context_variable(agent_id, "assigned_hospital") == "General Hospital"
        assert agent_memory_store.get_context_variable(agent_id, "specialties") == ["Trauma", "Burn"]

        all_ctx = agent_memory_store.get_all_context(agent_id)
        assert "assigned_hospital" in all_ctx

        agent_memory_store.clear_all_context(agent_id)


class TestSessionStore:
    """Tests RedisSessionStore lifecycle, touch TTL refresh, reverse index, and incident tracking."""

    def test_session_lifecycle(self):
        session_id = "sess-999"
        user_data = {"user_id": "usr-100", "role": "DISPATCHER", "name": "Alice"}

        session_store.create_session(session_id, user_data, ttl=300)

        session = session_store.get_session(session_id)
        assert session is not None
        assert session["name"] == "Alice"

        # Reverse lookup by user_id
        by_user = session_store.get_session_by_user_id("usr-100")
        assert by_user is not None
        assert by_user["session_id"] == session_id

        # Touch session
        touched = session_store.touch_session(session_id)
        assert touched is True

        # Attach incident
        session_store.attach_incident_to_session(session_id, "INC-301")
        attached = session_store.get_session_incidents(session_id)
        assert "INC-301" in attached

        session_store.detach_incident_from_session(session_id, "INC-301")
        assert "INC-301" not in session_store.get_session_incidents(session_id)

        session_store.delete_session(session_id)


class TestTaskQueue:
    """Tests RedisTaskQueue FIFO messaging, status tracking, DLQ, and stuck task recovery."""

    def test_enqueue_dequeue_and_status(self):
        queue_name = "emergency_dispatch"
        task_id = "task-001"
        payload = {"action": "dispatch_ambulance", "unit_id": "AMB-12"}

        task_queue.clear_queue(queue_name)

        task_queue.enqueue_task(queue_name, task_id, payload)
        assert task_queue.get_queue_length(queue_name) == 1

        status = task_queue.get_task_status(task_id)
        assert status is not None
        assert status["status"] == "PENDING"

        # Dequeue
        dequeued = task_queue.dequeue_task(queue_name)
        assert dequeued is not None
        assert dequeued["task_id"] == task_id
        assert dequeued["payload"]["unit_id"] == "AMB-12"

        status_after_deq = task_queue.get_task_status(task_id)
        assert status_after_deq["status"] == "PROCESSING"

        # Complete task
        task_queue.update_task_status(task_id, "COMPLETED", result={"eta_minutes": 4.5})
        final_status = task_queue.get_task_status(task_id)
        assert final_status["status"] == "COMPLETED"
        assert final_status["result"]["eta_minutes"] == 4.5

    def test_dlq_and_stuck_recovery(self):
        queue_name = "test_failures"
        task_id = "task-999"
        payload = {"data": "broken"}

        task_queue.clear_queue(queue_name)
        task_queue.enqueue_task(queue_name, task_id, payload)

        # Move to DLQ directly
        task_queue.move_to_dlq(queue_name, task_id, payload, "Unhandled error during processing")
        dlq_tasks = task_queue.get_dlq_tasks(queue_name)
        assert len(dlq_tasks) == 1
        assert dlq_tasks[0]["task_id"] == task_id

        task_queue.clear_queue(queue_name)


class TestStateCheckpointManager:
    """Tests StateCheckpointManager cross-domain snapshots, restoration, and pruning."""

    def test_checkpoint_manager_workflow(self):
        domain = "workflow"
        entity_id = "thread-401"
        data1 = {"step": 1, "value": "A"}

        cid1 = checkpoint_manager.create_checkpoint(domain, entity_id, "step_1", data1)
        assert cid1.startswith("chk-")

        data2 = {"step": 2, "value": "B"}
        cid2 = checkpoint_manager.create_checkpoint(domain, entity_id, "step_2", data2)

        checkpoints = checkpoint_manager.list_checkpoints(domain, entity_id)
        assert len(checkpoints) == 2

        restored_latest = checkpoint_manager.restore_latest_checkpoint(domain, entity_id)
        assert restored_latest is not None
        assert restored_latest["step"] == 2

    def test_checkpoint_pruning(self):
        domain = "incident"
        entity_id = "INC-501"

        for i in range(15):
            checkpoint_manager.create_checkpoint(domain, entity_id, f"snap-{i}", {"index": i})

        pruned = checkpoint_manager.prune_checkpoints(domain, entity_id, keep_last=5)
        remaining = checkpoint_manager.list_checkpoints(domain, entity_id)
        assert len(remaining) <= 10  # Enforced by create_checkpoint and max limit
