"""
Streamlit Real-Time Event Synchronizer

Connects background WebSocket client thread to Streamlit session state.
Drains incoming real-time events (Ambulance GPS, Hospital Beds, Agent Execution, Notifications)
and updates UI state automatically.
"""

import streamlit as st
import time
from frontend.websocket_client import ws_client


def init_realtime_connection():
    """Starts background WebSocket listener thread if not already running."""
    ws_client.start()


def sync_realtime_events():
    """
    Drains pending real-time events from WebSocket client event queue
    and applies updates directly into st.session_state.
    """
    init_realtime_connection()

    events = ws_client.get_pending_events()
    if not events:
        return 0

    incidents = st.session_state.get("incidents", [])
    ambulances = st.session_state.get("ambulances", [])
    hospitals = st.session_state.get("hospitals", [])

    updated_count = 0

    for evt in events:
        topic = evt.get("topic")
        data = evt.get("data", {})

        # Ambulance GPS Tracking Update
        if topic == "ambulance_tracking" and data:
            unit_id = data.get("unit_id")
            for amb in ambulances:
                if amb["unit_id"] == unit_id:
                    if "latitude" in data:
                        amb["latitude"] = data["latitude"]
                    if "longitude" in data:
                        amb["longitude"] = data["longitude"]
                    if "fuel_level_percent" in data:
                        amb["fuel_level_percent"] = data["fuel_level_percent"]
                    if "status" in data:
                        amb["status"] = data["status"]
                    updated_count += 1

        # Hospital ICU Capacity Update
        elif topic == "hospital_updates" and data:
            hospital_id = data.get("hospital_id")
            for hosp in hospitals:
                if hosp["hospital_id"] == hospital_id:
                    if "available_icu_beds" in data:
                        hosp["available_icu_beds"] = data["available_icu_beds"]
                    if "er_occupancy_percent" in data:
                        hosp["er_occupancy_percent"] = data["er_occupancy_percent"]
                    updated_count += 1

        # Agent Workflow Status Update
        elif topic == "agent_status" and data:
            incident_id = data.get("incident_id")
            for inc in incidents:
                if inc["incident_id"] == incident_id:
                    if "execution_stage" in data:
                        inc["execution_stage"] = data["execution_stage"]
                    if "status" in data:
                        inc["status"] = data["status"]
                    updated_count += 1

    return len(events)


def render_connection_status_badge():
    """Renders connection status indicator badge (WebSocket vs Polling Fallback)."""
    mode = ws_client.connection_mode

    if mode == "WEBSOCKET" or ws_client.is_connected:
        html = '<span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; padding: 3px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">● WS REALTIME CONNECTED</span>'
    elif mode == "POLLING_FALLBACK" or ws_client.is_polling_fallback:
        html = '<span style="background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid #f59e0b; padding: 3px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">🟡 HTTP POLLING FALLBACK</span>'
    else:
        html = '<span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; padding: 3px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">🔴 DISCONNECTED</span>'

    st.markdown(html, unsafe_allow_html=True)
