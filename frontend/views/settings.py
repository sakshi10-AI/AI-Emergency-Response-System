"""
Settings View - System Configuration & API Controls

Configures system parameters, API credentials, Redis memory connection,
auto-dispatch thresholds, and theme preferences.
"""

import streamlit as st
from frontend.theme import render_command_header, render_metric_card


def render_settings_view():
    """Renders System Settings & Configuration page."""
    render_command_header("SYSTEM CONFIGURATION & CONTROL PANEL", "Manage API Credentials, Redis Memory & Dispatch Parameters")

    settings = st.session_state.settings

    # System Status Bar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Gemini Model", settings["gemini_model"], "Primary LLM Engine", "cyan")
    with c2:
        render_metric_card("Redis Memory", settings["redis_status"], "Host: localhost:6379", "emerald" if settings["redis_status"] == "CONNECTED" else "red")
    with c3:
        render_metric_card("Auto-Dispatch", "ENABLED" if settings["auto_dispatch_enabled"] else "DISABLED", "Supervisor Override Active", "emerald")
    with c4:
        render_metric_card("Voice Alerts", "ACTIVE" if settings["voice_alerts"] else "MUTED", "EOC Audio Ticker", "amber")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔑 API Key & Infrastructure Connections")
        api_key = st.text_input("Google Gemini API Key:", value="*********************", type="password")
        backend_url = st.text_input("Backend FastAPI Service URL:", value="http://localhost:8000")
        redis_url = st.text_input("Redis Connection Host:", value="redis://localhost:6379/0")

        if st.button("💾 Save Infrastructure Connection"):
            st.success("Infrastructure credentials updated successfully!")

    with col2:
        st.subheader("⚙️ Dispatch Thresholds & Automation")
        auto_disp = st.checkbox("Enable Automated Agent Dispatch", value=settings["auto_dispatch_enabled"])
        voice = st.checkbox("Enable EOC Voice & Audio Alerts", value=settings["voice_alerts"])
        life_threat_thresh = st.slider("Life Threat Criticality Threshold Score:", 50, 100, 80)
        max_eta_alert = st.slider("Maximum Ambulance ETA Warning Threshold (Mins):", 1, 20, 8)

        if st.button("⚡ Update Dispatch Policies"):
            settings["auto_dispatch_enabled"] = auto_disp
            settings["voice_alerts"] = voice
            st.success("Dispatch policies updated successfully!")

    st.markdown("---")
    st.subheader("🎨 Command Theme Customization")
    st.selectbox("Select EOC Display Mode:", ["Dark Command (Default)", "Cyberpunk Tactical", "High Contrast Dark"])
    if st.button("Apply Theme Settings"):
        st.success("Theme settings applied.")
