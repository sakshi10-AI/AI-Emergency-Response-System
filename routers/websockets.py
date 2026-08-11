"""
FastAPI WebSocket Connection Manager & Real-Time Telemetry Router

Provides real-time streaming for:
- Agent Status Updates
- Computer Vision Detection Updates
- System Notifications & Alerts
- Ambulance GPS Tracking
- Hospital ICU Bed Capacity Updates
- Preempted Traffic Route Updates

Features heartbeat ping-pong handling, client subscription channels, and broadcast APIs.
"""

import asyncio
import json
import time
from typing import Dict, List, Set, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from utils.logger import app_logger

router = APIRouter(prefix="/api/v1/ws", tags=["Real-Time WebSockets"])


class WebSocketConnectionManager:
    """Manages active WebSocket connections, heartbeat pings, and topic broadcasts."""

    TOPICS = {
        "agent_status",
        "detection_updates",
        "notifications",
        "ambulance_tracking",
        "hospital_updates",
        "route_updates"
    }

    def __init__(self):
        # Maps websocket instance to set of subscribed topics
        self.active_connections: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, topics: Optional[List[str]] = None):
        """Accepts WebSocket connection and initializes subscriptions."""
        await websocket.accept()
        subscribed_topics = set(topics) if topics else set(self.TOPICS)
        self.active_connections[websocket] = subscribed_topics
        app_logger.info(f"[WebSocketManager] Client connected. Subscribed to topics: {subscribed_topics}")

        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_ack",
            "timestamp": time.time(),
            "subscribed_topics": list(subscribed_topics)
        })

    def disconnect(self, websocket: WebSocket):
        """Removes WebSocket connection from active pool."""
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            app_logger.info("[WebSocketManager] Client disconnected.")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Sends a JSON message to a single connected client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            app_logger.error(f"[WebSocketManager] Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast_event(self, topic: str, payload: Dict[str, Any]):
        """Broadcasts an event payload to all clients subscribed to the topic."""
        event_msg = {
            "topic": topic,
            "timestamp": time.time(),
            "data": payload
        }
        disconnected_clients = []

        for ws, subbed_topics in self.active_connections.items():
            if topic in subbed_topics or "all" in subbed_topics:
                try:
                    await ws.send_json(event_msg)
                except Exception as e:
                    app_logger.warning(f"[WebSocketManager] Failed broadcast to client: {e}")
                    disconnected_clients.append(ws)

        for ws in disconnected_clients:
            self.disconnect(ws)

    def get_connection_count(self) -> int:
        """Returns total active connected clients."""
        return len(self.active_connections)


# Global Singleton Manager Instance
ws_manager = WebSocketConnectionManager()


@router.websocket("")
@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    topics: Optional[str] = Query(None, description="Comma-separated topics to subscribe to")
):
    """
    Main WebSocket endpoint (`ws://host:port/api/v1/ws`).
    Handles client subscriptions, heartbeat pings, and real-time event streaming.
    """
    topic_list = [t.strip() for t in topics.split(",")] if topics else None
    await ws_manager.connect(websocket, topics=topic_list)

    try:
        while True:
            # Receive text/json from client
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                msg_type = msg.get("type", "").lower()

                # Heartbeat Ping -> Pong response
                if msg_type == "ping":
                    await ws_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": time.time()
                    }, websocket)

                # Dynamic Topic Subscription
                elif msg_type == "subscribe":
                    new_topics = msg.get("topics", [])
                    if websocket in ws_manager.active_connections:
                        ws_manager.active_connections[websocket].update(new_topics)
                        await ws_manager.send_personal_message({
                            "type": "subscribe_ack",
                            "subscribed_topics": list(ws_manager.active_connections[websocket])
                        }, websocket)

            except json.JSONDecodeError:
                app_logger.warning(f"[WebSocketEndpoint] Received invalid JSON: {raw_text[:50]}")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        app_logger.error(f"[WebSocketEndpoint] Exception in WebSocket connection: {e}")
        ws_manager.disconnect(websocket)
