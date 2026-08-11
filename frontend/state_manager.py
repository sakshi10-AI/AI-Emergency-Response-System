"""
Streamlit Centralized State Manager

Initializes and manages st.session_state across all independent dashboard views.
Fetches live data through API Service Clients on first load; falls back to mock data
if the backend is offline. Guarantees zero key collisions and seamless inter-page
state persistence.
"""

import streamlit as st
from frontend.api_clients.mock_data import (
    MOCK_INCIDENTS,
    MOCK_HOSPITALS,
    MOCK_AMBULANCES,
    MOCK_CAMERA_STREAMS,
)


def _fetch_incidents():
    """Loads incidents via IncidentClient with mock fallback."""
    try:
        from frontend.api_clients.incident_client import incident_client
        data = incident_client.get_incidents()
        return data if data else list(MOCK_INCIDENTS)
    except Exception:
        return list(MOCK_INCIDENTS)


def _fetch_hospitals():
    """Loads hospitals via HospitalClient with mock fallback."""
    try:
        from frontend.api_clients.hospital_client import hospital_client
        data = hospital_client.get_hospitals()
        return data if data else list(MOCK_HOSPITALS)
    except Exception:
        return list(MOCK_HOSPITALS)


def _fetch_ambulances():
    """Loads ambulances via AmbulanceClient with mock fallback."""
    try:
        from frontend.api_clients.ambulance_client import ambulance_client
        data = ambulance_client.get_ambulances()
        return data if data else list(MOCK_AMBULANCES)
    except Exception:
        return list(MOCK_AMBULANCES)


def init_session_state():
    """Initializes global session state variables if not already present."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    if "selected_incident_id" not in st.session_state:
        st.session_state.selected_incident_id = "INC-8821"

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "auth_token" not in st.session_state:
        st.session_state.auth_token = None

    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    # --- Live Data (fetched from API; falls back to mock) ---
    if "incidents" not in st.session_state:
        st.session_state.incidents = _fetch_incidents()

    if "hospitals" not in st.session_state:
        st.session_state.hospitals = _fetch_hospitals()

    if "ambulances" not in st.session_state:
        st.session_state.ambulances = _fetch_ambulances()

    if "camera_streams" not in st.session_state:
        st.session_state.camera_streams = list(MOCK_CAMERA_STREAMS)

    # System Settings
    if "settings" not in st.session_state:
        st.session_state.settings = {
            "api_key_set": True,
            "auto_dispatch_enabled": True,
            "voice_alerts": True,
            "theme_mode": "Dark Command",
            "redis_status": "CONNECTED",
            "gemini_model": "gemini-2.5-flash"
        }

    # Video analysis state
    if "video_analyzed" not in st.session_state:
        st.session_state.video_analyzed = False


def refresh_incidents():
    """Force-refreshes incidents from API into session state."""
    st.session_state.incidents = _fetch_incidents()


def refresh_hospitals():
    """Force-refreshes hospital data from API into session state."""
    st.session_state.hospitals = _fetch_hospitals()


def refresh_ambulances():
    """Force-refreshes ambulance fleet data from API into session state."""
    st.session_state.ambulances = _fetch_ambulances()


def set_auth_token(token: str, user: dict):
    """Persists authenticated session token and user into state."""
    from frontend.api_clients.base_client import base_api_client
    st.session_state.auth_token = token
    st.session_state.authenticated = True
    st.session_state.current_user = user
    base_api_client.set_auth_token(token)
