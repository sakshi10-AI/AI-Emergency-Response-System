"""
Streamlit Authentication & Role-Based Access Control Guard

Manages role-based page navigation permissions and action authorizations for:
- Admin (Full 10 pages + settings + overrides)
- Dispatcher (9 pages, dispatch approvals, unit assignments)
- Police (8 pages, surveillance, traffic clearance, incident updates)
- Hospital (5 pages, bed reservations, trauma matrix, incoming ETAs)
- Viewer (3 pages, read-only analytics & dashboards)
"""

import streamlit as st
from typing import List, Dict, Set


ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": [
        "Dashboard", "Live Camera", "🎥 Webcam AI", "Upload Video", "Upload Image",
        "Incident Details", "Hospital Dashboard", "Ambulance Dashboard",
        "Analytics", "Reports", "Settings"
    ],
    "dispatcher": [
        "Dashboard", "Live Camera", "🎥 Webcam AI", "Upload Video", "Upload Image",
        "Incident Details", "Hospital Dashboard", "Ambulance Dashboard",
        "Analytics", "Reports"
    ],
    "police": [
        "Dashboard", "Live Camera", "🎥 Webcam AI", "Upload Video", "Upload Image",
        "Incident Details", "Ambulance Dashboard", "Analytics", "Reports"
    ],
    "hospital": [
        "Dashboard", "Incident Details", "Hospital Dashboard",
        "Analytics", "Reports"
    ],
    "viewer": [
        "Dashboard", "Analytics", "Reports"
    ]
}


def get_allowed_pages(role: str) -> List[str]:
    """Returns list of allowed navigation page names for the user's role."""
    clean_role = (role or "viewer").lower()
    return ROLE_PERMISSIONS.get(clean_role, ROLE_PERMISSIONS["viewer"])


def has_page_access(role: str, page: str) -> bool:
    """Checks if a user role is authorized to view a specific page."""
    allowed = get_allowed_pages(role)
    return page in allowed


def render_access_denied_card(page_name: str, required_roles: str = "higher privilege"):
    """Renders a sleek Access Denied warning card if permission is missing."""
    html = f"""
    <div style="background-color: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; border-left: 5px solid #ef4444; padding: 1.5rem; border-radius: 8px; margin-top: 2rem;">
        <h3 style="color: #ef4444; margin-top: 0;">🔒 ACCESS DENIED — RESTRICTED PAGE</h3>
        <p style="color: #e5e7eb;">Your active role (<b>{st.session_state.get('current_user', {}).get('role', 'VIEWER').upper()}</b>) is not authorized to access <b>{page_name}</b>.</p>
        <p style="color: #9ca3af; font-size: 0.85rem;">Required permission level: <b>{required_roles}</b>. Contact EOC System Administrator to request elevated role access.</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
