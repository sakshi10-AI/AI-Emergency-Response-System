"""
Streamlit Presentation UI - Emergency Operations Command Center

Main entry point for the Emergency Operations Center (EOC) Dashboard.
Manages dark command theme, authentication verification, role-based navigation filtering,
and modular page execution.
"""
import sys
import os
from pathlib import Path

# Ensure project root directory is present in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
from frontend.theme import inject_custom_theme
from frontend.state_manager import init_session_state
from frontend.auth_guard import get_allowed_pages, has_page_access, render_access_denied_card
from frontend.realtime_sync import sync_realtime_events, render_connection_status_badge

# View Module Imports
from frontend.views.login_view import render_login_view
from frontend.views.dashboard import render_dashboard_view
from frontend.views.live_camera import render_live_camera_view
from frontend.views.webcam_analysis import render_webcam_analysis_view
from frontend.views.upload_video import render_upload_video_view
from frontend.views.upload_image import render_upload_image_view
from frontend.views.incident_details import render_incident_details_view
from frontend.views.hospital_dashboard import render_hospital_dashboard_view
from frontend.views.ambulance_dashboard import render_ambulance_dashboard_view
from frontend.views.analytics import render_analytics_view
from frontend.views.reports import render_reports_view
from frontend.views.settings import render_settings_view

# Page Config
st.set_page_config(
    page_title="Nagpur EOC | AI Emergency Response System",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Complete Page Mapping Dictionary
ALL_PAGES = {
    "Dashboard": render_dashboard_view,
    "Live Camera": render_live_camera_view,
    "🎥 Webcam AI": render_webcam_analysis_view,
    "Upload Video": render_upload_video_view,
    "Upload Image": render_upload_image_view,
    "Incident Details": render_incident_details_view,
    "Hospital Dashboard": render_hospital_dashboard_view,
    "Ambulance Dashboard": render_ambulance_dashboard_view,
    "Analytics": render_analytics_view,
    "Reports": render_reports_view,
    "Settings": render_settings_view
}


def main():
    """Main application loop."""
    # 1. Inject Custom Dark Theme CSS
    inject_custom_theme()

    # 2. Initialize Session State Variables
    init_session_state()

    # 3. Check Authentication Status
    if not st.session_state.get("authenticated", False):
        render_login_view()
        return

    # 4. Sync Real-Time Telemetry Events
    sync_realtime_events()

    # 5. Extract Current User Role & Determine Allowed Pages
    current_user = st.session_state.get("current_user", {})
    user_name = current_user.get("name", current_user.get("username", "Officer"))
    user_role = (current_user.get("role") or "viewer").lower()

    allowed_page_names = get_allowed_pages(user_role)

    # 6. Sidebar Navigation Engine
    st.sidebar.markdown("## 🚨 EOC COMMAND CENTER")
    st.sidebar.markdown("**AI Emergency Response Platform**")

    # Render User Profile Card in Sidebar
    role_color = {
        "admin": "#ef4444",
        "dispatcher": "#06b6d4",
        "police": "#3b82f6",
        "hospital": "#10b981",
        "viewer": "#f59e0b"
    }.get(user_role, "#9ca3af")

    st.sidebar.markdown(f"""
    <div style="background-color: #1f2937; border-left: 4px solid {role_color}; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem;">
        <div style="font-weight: bold; color: #f9fafb; font-size: 0.95rem;">👤 {user_name}</div>
        <div style="font-size: 0.75rem; color: {role_color}; font-weight: bold; text-transform: uppercase;">ROLE: {user_role.upper()}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout Officer Session", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.auth_token = None
        st.session_state.current_user = None
        st.rerun()

    st.sidebar.markdown("---")

    # Icons mapping
    page_icons = {
        "Dashboard": "📊",
        "Live Camera": "📹",
        "Upload Video": "🎥",
        "Upload Image": "📷",
        "Incident Details": "🔍",
        "Hospital Dashboard": "🏥",
        "Ambulance Dashboard": "🚑",
        "Analytics": "📈",
        "Reports": "📑",
        "Settings": "⚙️"
    }

    # Ensure selected page is within allowed pages
    if st.session_state.current_page not in allowed_page_names:
        st.session_state.current_page = allowed_page_names[0]

    default_idx = allowed_page_names.index(st.session_state.current_page)

    selected_page = st.sidebar.radio(
        "NAVIGATION MENU",
        options=allowed_page_names,
        index=default_idx,
        format_func=lambda page: f"{page_icons.get(page, '▪')} {page}"
    )

    st.session_state.current_page = selected_page

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🟢 Telemetry & Security")
    render_connection_status_badge()
    st.sidebar.caption(f"🔒 **RBAC Enforcement:** {user_role.upper()} ({len(allowed_page_names)} Pages)")

    # 7. Render Target Authorized Page View
    if has_page_access(user_role, selected_page):
        view_func = ALL_PAGES.get(selected_page, render_dashboard_view)
        view_func()
    else:
        render_access_denied_card(selected_page, f"Required: Higher role than {user_role.upper()}")


if __name__ == "__main__":
    main()
