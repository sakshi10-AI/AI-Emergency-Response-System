"""
Ambulance Dashboard View - Emergency Response Fleet Management

Tracks emergency medical fleet, active dispatches, GPS telemetry, fuel/equipment levels,
and traffic signal preemption status.
"""

import streamlit as st
import pandas as pd
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients import ambulance_client
from frontend.state_manager import refresh_ambulances


def render_ambulance_dashboard_view():
    """Renders Ambulance Fleet Management page."""
    render_command_header("EMERGENCY MEDICAL FLEET COMMAND", "Real-Time Ambulance Telemetry, Unit Dispatch & Equipment Readiness")

    ambulances = st.session_state.ambulances

    total_fleet = len(ambulances)
    dispatched = len([a for a in ambulances if a["status"] in ["DISPATCHED", "EN_ROUTE"]])
    available = len([a for a in ambulances if a["status"] == "AVAILABLE"])
    avg_fuel = sum(a["fuel_level_percent"] for a in ambulances) // total_fleet

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Total Fleet Units", str(total_fleet), "ALS / BLS / Air Rescue", "cyan")
    with c2:
        render_metric_card("Active Dispatches", str(dispatched), "In Transit to Incidents", "amber")
    with c3:
        render_metric_card("Units Available", str(available), "Ready for Station Dispatch", "emerald")
    with c4:
        render_metric_card("Fleet Fuel Level", f"{avg_fuel}%", "Average Readiness", "cyan")

    st.markdown("---")

    # Ambulance Units Cards
    st.subheader("🚑 Unit Telemetry & Equipment Matrix")
    for amb in ambulances:
        with st.expander(f"🚑 {amb['call_sign']} ({amb['unit_id']}) - Status: {amb['status']}", expanded=True):
            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                st.markdown(f"**Unit Type:** `{amb['unit_type']}`")
                st.markdown(f"**Assigned Incident:** `{amb['assigned_incident']}`")
                st.markdown(f"**ETA to Scene/Hospital:** `{amb['eta_minutes']} mins`")

            with col2:
                st.markdown(f"**Fuel / Battery:** {amb['fuel_level_percent']}%")
                st.progress(amb['fuel_level_percent'])
                st.markdown(f"**GPS Coords:** {amb['latitude']}, {amb['longitude']}")

            with col3:
                st.markdown("**Installed Equipment:**")
                for eq in amb["equipment"]:
                    st.markdown(f"✓ `{eq}`")

                new_status = st.selectbox(
                    f"Update Unit Status ({amb['unit_id']}):",
                    ["AVAILABLE", "DISPATCHED", "EN_ROUTE", "TRANSPORTING", "AT_HOSPITAL"],
                    index=["AVAILABLE", "DISPATCHED", "EN_ROUTE", "TRANSPORTING", "AT_HOSPITAL"].index(amb["status"]),
                    key=f"status_select_{amb['unit_id']}"
                )
                if new_status != amb["status"]:
                    result = ambulance_client.update_unit_status(amb["unit_id"], new_status)
                    amb["status"] = new_status
                    st.success(f"Status updated to {new_status} via API ({result.get('status', 'OK')})")
                    refresh_ambulances()
                    st.rerun()

    st.markdown("---")
    st.subheader("🚦 Active Signal Preemption & Corridor Clearance")
    st.info("🟢 Green Corridor active along Wardha Road towards Ajni Square for Nagpur Medic 101. 4 traffic signals preempted.")
