"""
Incident Details View - Deep-Dive Incident Inspection & Workflow Command

Displays complete multi-agent workflow state execution, interactive route map,
chronological event audit logs, and supervisor override controls.
All actions routed exclusively through API Service Clients.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients import incident_client, notification_client


def render_incident_details_view():
    """Renders Incident Details Command Inspection page."""
    incidents = st.session_state.incidents
    sel_id = st.session_state.get("selected_incident_id", "INC-8821")

    # Find target incident or fallback
    incident = next((i for i in incidents if i["incident_id"] == sel_id), incidents[0])

    render_command_header(f"INCIDENT COMMAND DETAILS: {incident['incident_id']}", f"Tracking Code: {incident['tracking_code']} | Status: {incident['status']}")

    # Incident Selection Dropdown
    curr_sel = st.selectbox(
        "Switch Inspected Incident:",
        options=[i["incident_id"] for i in incidents],
        index=[i["incident_id"] for i in incidents].index(incident["incident_id"])
    )
    if curr_sel != incident["incident_id"]:
        st.session_state.selected_incident_id = curr_sel
        st.rerun()

    # Workflow Execution Stage Progress Bar
    st.subheader("⚡ LangGraph Multi-Agent Workflow Execution Pipeline")
    stages = ["INIT", "VISION", "SEVERITY", "HOSPITAL", "AMBULANCE", "TRAFFIC", "DISPATCHED"]
    current_stage = "DISPATCHED" if incident["status"] == "DISPATCHED" else "SEVERITY"
    curr_idx = stages.index(current_stage) if current_stage in stages else 3
    progress_val = int((curr_idx + 1) / len(stages) * 100)

    st.progress(progress_val)
    cols = st.columns(len(stages))
    for idx, stage in enumerate(stages):
        with cols[idx]:
            if idx <= curr_idx:
                st.markdown(f"**🟢 {stage}**")
            else:
                st.markdown(f"⚪ {stage}")

    st.markdown("---")

    # High-level details card
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Priority Level", incident["priority_category"], f"Severity Scale: {incident['severity_level']}", "red")
    with c2:
        render_metric_card("Reported Address", incident["address"], f"Coords: {incident['latitude']}, {incident['longitude']}", "cyan")
    with c3:
        render_metric_card("Assigned Ambulance", incident["assigned_ambulance"], f"ETA: {incident['eta_minutes']} mins", "amber")
    with c4:
        render_metric_card("Assigned Hospital", incident["assigned_hospital"], "Level I Trauma Match", "emerald")

    st.markdown("---")

    # Layout: Map on left, Audit Log on right
    map_col, log_col = st.columns([1.5, 1])

    with map_col:
        st.subheader("🗺️ Emergency Transit & Routing Map")
        m = folium.Map(location=[incident["latitude"], incident["longitude"]], zoom_start=14, tiles="CartoDB dark_matter")

        # Incident Marker
        folium.Marker(
            location=[incident["latitude"], incident["longitude"]],
            popup=f"<b>INCIDENT SCENE</b><br>{incident['title']}",
            tooltip=incident["incident_id"],
            icon=folium.Icon(color="red", icon="fire", prefix="fa")
        ).add_to(m)

        # Assigned Hospital Marker
        hosp_lat, hosp_lng = 21.1367, 79.0995  # GMCH Nagpur
        folium.Marker(
            location=[hosp_lat, hosp_lng],
            popup=f"<b>HOSPITAL: {incident['assigned_hospital']}</b>",
            tooltip=incident["assigned_hospital"],
            icon=folium.Icon(color="purple", icon="hospital", prefix="fa")
        ).add_to(m)

        # Route Line
        folium.PolyLine(
            locations=[[incident["latitude"], incident["longitude"]], [hosp_lat, hosp_lng]],
            color="#06b6d4",
            weight=4,
            opacity=0.8,
            tooltip="Optimal Preempted Emergency Route"
        ).add_to(m)

        st_folium(m, width="100%", height=380)

    with log_col:
        st.subheader("📜 Event Log Audit Timeline")
        timeline = incident_client.get_incident_timeline(incident["incident_id"])
        for evt in timeline:
            if isinstance(evt, dict):
                st.markdown(f"⏱️ **{evt.get('time', '')}** | `{evt.get('source', 'System')}`: {evt.get('event', '')}")
            else:
                st.markdown(f"⏱️ {evt}")

    st.markdown("---")

    # Supervisor Manual Override Panel
    st.subheader("🛡️ Supervisor Manual Override Controls")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        if st.button("✅ Confirm Dispatch Approval"):
            result = incident_client.approve_dispatch(incident["incident_id"], notes="Supervisor approved")
            st.success(f"Dispatch confirmed! Status: {result.get('status', 'OK')}")
    with sc2:
        if st.button("🔁 Re-route Ambulance"):
            result = incident_client.update_incident_status(incident["incident_id"], "REROUTING")
            st.warning(f"Ambulance re-routing requested. ({result.get('status', '')})")
    with sc3:
        if st.button("🏥 Switch Hospital Target"):
            st.info("Hospital destination selection opened.")
    with sc4:
        if st.button("📢 Issue Public SMS Alert"):
            result = notification_client.broadcast_public_sms(
                sector="Sector 4",
                alert_text=f"Emergency alert: {incident['title']}. Avoid affected area.",
                severity="CRITICAL"
            )
            st.error(f"Public alert broadcast! Status: {result.get('status', 'SENT')}")
