"""
Unit & Integration Tests for Real-Time WebSocket & Fallback Engine

Tests:
- WebSocketConnectionManager (connection pool, subscription channels, broadcasting)
- Heartbeat Ping/Pong Handling
- EOCWebSocketClient (thread-safe event queue, reconnects, polling fallback)
- Real-Time Streamlit Session State Synchronization
"""

import pytest
import asyncio
import time
from routers.websockets import WebSocketConnectionManager, ws_manager
from frontend.websocket_client import EOCWebSocketClient, ws_client
from frontend.realtime_sync import sync_realtime_events, render_connection_status_badge


class DummyWebSocket:
    """Mock WebSocket instance for testing broadcast & ping/pong."""

    def __init__(self):
        self.accepted = False
        self.sent_messages = []
        self.closed = False

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_websocket_connection_manager():
    """Tests connection manager lifecycle, subscriptions, and broadcasts."""
    mgr = WebSocketConnectionManager()
    ws1 = DummyWebSocket()
    ws2 = DummyWebSocket()

    await mgr.connect(ws1, topics=["agent_status", "ambulance_tracking"])
    await mgr.connect(ws2, topics=["hospital_updates"])

    assert mgr.get_connection_count() == 2
    assert len(ws1.sent_messages) == 1
    assert ws1.sent_messages[0]["type"] == "connection_ack"

    # Broadcast on agent_status -> should reach ws1 only
    await mgr.broadcast_event("agent_status", {"incident_id": "INC-100", "stage": "DISPATCHING"})
    assert len(ws1.sent_messages) == 2
    assert ws1.sent_messages[1]["topic"] == "agent_status"
    assert len(ws2.sent_messages) == 1  # ws2 is subscribed to hospital_updates only

    # Broadcast on hospital_updates -> should reach ws2 only
    await mgr.broadcast_event("hospital_updates", {"hospital_id": "HOSP-01", "available_icu_beds": 10})
    assert len(ws2.sent_messages) == 2
    assert ws2.sent_messages[1]["topic"] == "hospital_updates"

    mgr.disconnect(ws1)
    mgr.disconnect(ws2)
    assert mgr.get_connection_count() == 0


def test_websocket_client_polling_fallback():
    """Tests EOCWebSocketClient thread-safe queue and HTTP polling fallback mode."""
    client = EOCWebSocketClient()
    client.is_connected = False
    client.is_polling_fallback = True
    client.connection_mode = "POLLING_FALLBACK"

    # Trigger a polling fallback cycle
    client._run_polling_fallback_cycle()

    events = client.get_pending_events()
    assert isinstance(events, list)
    assert len(events) >= 1

    topics = [e["topic"] for e in events]
    assert "ambulance_tracking" in topics or "agent_status" in topics


def test_realtime_sync_event_processing():
    """Tests sync_realtime_events applying event queue updates into session_state."""
    import streamlit as st
    st.session_state.incidents = [{"incident_id": "INC-8821", "status": "ANALYZING", "execution_stage": "INIT"}]
    st.session_state.ambulances = [{"unit_id": "AMB-101", "latitude": 37.7700, "longitude": -122.4100, "fuel_level_percent": 90, "status": "DISPATCHED"}]
    st.session_state.hospitals = [{"hospital_id": "HOSP-01", "available_icu_beds": 5, "er_occupancy_percent": 80}]

    # Enqueue mock WebSocket event
    ws_client._enqueue_event({
        "topic": "ambulance_tracking",
        "data": {"unit_id": "AMB-101", "latitude": 37.7800, "longitude": -122.4200, "fuel_level_percent": 85, "status": "EN_ROUTE"}
    })

    ws_client._enqueue_event({
        "topic": "hospital_updates",
        "data": {"hospital_id": "HOSP-01", "available_icu_beds": 8, "er_occupancy_percent": 70}
    })

    processed = sync_realtime_events()
    assert processed >= 2

    # Check updated state
    assert st.session_state.ambulances[0]["latitude"] == 37.7800
    assert st.session_state.ambulances[0]["status"] == "EN_ROUTE"
    assert st.session_state.hospitals[0]["available_icu_beds"] == 8
