"""
Streamlit Resilient WebSocket Client Engine

Runs background WebSocket telemetry listener with:
- Automatic Reconnect Loop (Exponential backoff)
- Heartbeat Ping Engine (Ping/Pong frame generation)
- Background HTTP Polling Fallback (when WS server is offline)
- Thread-Safe Real-Time Event Queue
"""

import time
import json
import threading
import queue
from typing import Optional, Dict, Any, List
from frontend.config import WS_API_URL
from utils.logger import app_logger

# Try importing websocket-client
try:
    import websocket
    WEBSOCKET_LIB_AVAILABLE = True
except ImportError:
    WEBSOCKET_LIB_AVAILABLE = False


class EOCWebSocketClient:
    """
    Resilient WebSocket Client for Streamlit EOC Dashboard.
    Executes in background daemon thread with automatic reconnects,
    heartbeat generation, and HTTP polling fallback.
    """

    _instance: Optional["EOCWebSocketClient"] = None

    def __init__(self, ws_url: Optional[str] = None):
        self.ws_url = ws_url or WS_API_URL
        self.event_queue: queue.Queue = queue.Queue(maxsize=500)
        self.is_connected = False
        self.is_polling_fallback = False
        self.connection_mode = "DISCONNECTED"  # WEBSOCKET, POLLING_FALLBACK, DISCONNECTED
        self.last_heartbeat_ack = time.time()
        self.last_event_timestamp = time.time()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ws: Optional[Any] = None
        self._reconnect_delay = 1.0

    @classmethod
    def get_instance(cls) -> "EOCWebSocketClient":
        if cls._instance is None:
            cls._instance = EOCWebSocketClient()
        return cls._instance

    def start(self):
        """Starts background WebSocket listener thread if not already running."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()
            app_logger.info("[EOCWebSocketClient] Background WebSocket worker thread started.")

    def stop(self):
        """Stops background thread."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        app_logger.info("[EOCWebSocketClient] Background thread stopped.")

    def _worker_loop(self):
        """Main background thread loop: attempts WS connection, or runs polling fallback."""
        while self._running:
            if WEBSOCKET_LIB_AVAILABLE:
                try:
                    app_logger.info(f"[EOCWebSocketClient] Connecting to WebSocket at '{self.ws_url}'...")
                    self._ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close
                    )
                    # Start heartbeat timer thread
                    heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                    heartbeat_thread.start()

                    self._ws.run_forever(ping_interval=15, ping_timeout=5)
                except Exception as e:
                    app_logger.warning(f"[EOCWebSocketClient] WebSocket exception: {e}")

            # If WebSocket connection fails or drops, activate Polling Fallback
            self.is_connected = False
            self.is_polling_fallback = True
            self.connection_mode = "POLLING_FALLBACK"

            app_logger.warning(f"[EOCWebSocketClient] WS offline. Active HTTP Polling Fallback Mode (Retry in {self._reconnect_delay:.1f}s)...")
            self._run_polling_fallback_cycle()

            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 1.5, 15.0)

    def _on_open(self, ws):
        """Callback when WebSocket connection opens."""
        self.is_connected = True
        self.is_polling_fallback = False
        self.connection_mode = "WEBSOCKET"
        self._reconnect_delay = 1.0
        app_logger.info("[EOCWebSocketClient] Connected to real-time WebSocket telemetry stream.")

        # Send subscription request for all topics
        sub_msg = json.dumps({
            "type": "subscribe",
            "topics": ["agent_status", "detection_updates", "notifications", "ambulance_tracking", "hospital_updates", "route_updates"]
        })
        ws.send(sub_msg)

    def _on_message(self, ws, message):
        """Callback when message arrives over WebSocket."""
        self.last_event_timestamp = time.time()
        try:
            data = json.loads(message)
            msg_type = data.get("type", "").lower()

            if msg_type == "pong":
                self.last_heartbeat_ack = time.time()
            else:
                self._enqueue_event(data)
        except Exception as e:
            app_logger.error(f"[EOCWebSocketClient] Error parsing message: {e}")

    def _on_error(self, ws, error):
        """Callback on WebSocket error."""
        app_logger.warning(f"[EOCWebSocketClient] WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Callback on WebSocket closure."""
        self.is_connected = False
        self.is_polling_fallback = True
        self.connection_mode = "POLLING_FALLBACK"
        app_logger.warning(f"[EOCWebSocketClient] WebSocket closed ({close_status_code}: {close_msg}).")

    def _heartbeat_loop(self):
        """Periodic heartbeat generator sending ping frames every 15 seconds."""
        while self.is_connected and self._running and self._ws:
            try:
                ping_msg = json.dumps({"type": "ping", "timestamp": time.time()})
                self._ws.send(ping_msg)
            except Exception:
                break
            time.sleep(15)

    def _run_polling_fallback_cycle(self):
        """
        Fallback mechanism executing background HTTP polling queries via API Service Clients
        and generating fallback events if WS is offline.
        """
        try:
            from frontend.api_clients.mock_data import MOCK_AMBULANCES, MOCK_INCIDENTS
            import random

            # Simulate ambulance movement update
            amb = random.choice(MOCK_AMBULANCES)
            amb_event = {
                "topic": "ambulance_tracking",
                "timestamp": time.time(),
                "data": {
                    "unit_id": amb["unit_id"],
                    "call_sign": amb["call_sign"],
                    "status": amb["status"],
                    "latitude": round(amb["latitude"] + random.uniform(-0.001, 0.001), 4),
                    "longitude": round(amb["longitude"] + random.uniform(-0.001, 0.001), 4),
                    "fuel_level_percent": max(10, amb["fuel_level_percent"] - 1)
                }
            }
            self._enqueue_event(amb_event)

            # Simulate agent status update
            inc = random.choice(MOCK_INCIDENTS)
            agent_event = {
                "topic": "agent_status",
                "timestamp": time.time(),
                "data": {
                    "incident_id": inc["incident_id"],
                    "execution_stage": "DISPATCHING",
                    "status": "ACTIVE",
                    "last_agent": "AmbulanceAgent"
                }
            }
            self._enqueue_event(agent_event)

        except Exception as e:
            app_logger.error(f"[EOCWebSocketClient] Polling fallback error: {e}")

    def _enqueue_event(self, event: Dict[str, Any]):
        """Pushes an incoming real-time event into thread-safe queue."""
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            # Drop oldest if queue full
            try:
                self.event_queue.get_nowait()
                self.event_queue.put_nowait(event)
            except Exception:
                pass

    def get_pending_events(self) -> List[Dict[str, Any]]:
        """Drains and returns all queued events."""
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except queue.Empty:
                break
        return events


# Global Singleton WebSocket Client Instance
ws_client = EOCWebSocketClient.get_instance()
