"""
Dashboard View - Main Emergency Operations Overview

Displays real-time KPI metrics, interactive Folium tactical map,
Plotly analytics charts, and the active emergency incident dispatch queue.
All data fetched exclusively through API Service Clients.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients import incident_client, hospital_client, ambulance_client, notification_client
from frontend.state_manager import refresh_incidents, refresh_hospitals, refresh_ambulances


def render_dashboard_view():
    """Renders main EOC Dashboard page."""
    render_command_header("OPERATIONAL DASHBOARD", "Real-Time Emergency Operations & Tactical Dispatch Overview")

    # Refresh data controls
    col_ref1, col_ref2, col_ref3, col_ref4 = st.columns([1, 1, 1, 4])
    with col_ref1:
        if st.button("🔄 Refresh Incidents"):
            refresh_incidents()
            st.rerun()
    with col_ref2:
        if st.button("🔄 Refresh Hospitals"):
            refresh_hospitals()
            st.rerun()
    with col_ref3:
        if st.button("🔄 Refresh Fleet"):
            refresh_ambulances()
            st.rerun()

    incidents = st.session_state.incidents
    hospitals = st.session_state.hospitals
    ambulances = st.session_state.ambulances

    # KPI Top Bar Metrics
    col1, col2, col3, col4 = st.columns(4)
    active_count = len([i for i in incidents if i["status"] != "COMPLETED"])
    critical_count = len([i for i in incidents if i["priority_category"] == "CRITICAL"])
    dispatched_units = len([a for a in ambulances if a["status"] in ["DISPATCHED", "EN_ROUTE"]])
    avg_icu = int(sum(h["available_icu_beds"] for h in hospitals) / len(hospitals)) if hospitals else 0

    with col1:
        render_metric_card("Active Incidents", str(active_count), "Requires EOC Monitoring", "cyan")
    with col2:
        render_metric_card("Critical Hazards", str(critical_count), "High Life Threat Priority", "red")
    with col3:
        render_metric_card("Units Dispatched", str(dispatched_units), "En Route to Scenes", "amber")
    with col4:
        render_metric_card("ICU Beds Free", str(avg_icu), "Regional Average", "emerald")

    st.markdown("---")

    # Layout: Map on left, Charts on right
    map_col, chart_col = st.columns([1.6, 1])

    with map_col:
        st.subheader("🗺️ Tactical Geographic Command Map")
        # Center map on average lat/lng
        m = folium.Map(location=[21.1458, 79.0882], zoom_start=13, tiles="CartoDB dark_matter")  # Nagpur, India

        # Incident Markers
        for inc in incidents:
            color = "red" if inc["priority_category"] == "CRITICAL" else ("orange" if inc["priority_category"] == "URGENT" else "blue")
            popup_text = f"<b>{inc['incident_id']}: {inc['title']}</b><br>Status: {inc['status']}<br>Address: {inc['address']}"
            folium.Marker(
                location=[inc["latitude"], inc["longitude"]],
                popup=popup_text,
                tooltip=f"{inc['incident_id']} ({inc['priority_category']})",
                icon=folium.Icon(color=color, icon="fire", prefix="fa")
            ).add_to(m)

        # Ambulance Markers
        for amb in ambulances:
            folium.Marker(
                location=[amb["latitude"], amb["longitude"]],
                popup=f"<b>{amb['call_sign']} ({amb['unit_id']})</b><br>Status: {amb['status']}<br>Assigned: {amb['assigned_incident']}",
                tooltip=amb["call_sign"],
                icon=folium.Icon(color="green", icon="ambulance", prefix="fa")
            ).add_to(m)

        # Hospital Markers
        for hosp in hospitals:
            folium.Marker(
                location=[hosp["latitude"], hosp["longitude"]],
                popup=f"<b>{hosp['name']}</b><br>ICU Available: {hosp['available_icu_beds']}/{hosp['total_icu_beds']}",
                tooltip=f"{hosp['name']} ({hosp['trauma_level']})",
                icon=folium.Icon(color="purple", icon="hospital", prefix="fa")
            ).add_to(m)

        st_folium(m, width="100%", height=420)

    with chart_col:
        st.subheader("📊 Incident Analytics")

        # Severity Breakdown Chart
        sev_df = pd.DataFrame(incidents)
        if not sev_df.empty:
            fig_sev = px.bar(
                sev_df,
                x="priority_category",
                color="priority_category",
                title="Active Incidents by Priority",
                color_discrete_map={"CRITICAL": "#ef4444", "URGENT": "#f59e0b", "MINOR": "#10b981"},
                template="plotly_dark"
            )
            fig_sev.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=200, showlegend=False)
            st.plotly_chart(fig_sev, use_container_width=True)

            # Hospital Bed Occupancy Donut
            hosp_df = pd.DataFrame(hospitals)
            fig_hosp = px.pie(
                hosp_df,
                values="available_icu_beds",
                names="name",
                title="Available ICU Bed Distribution",
                hole=0.4,
                template="plotly_dark"
            )
            fig_hosp.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=200)
            st.plotly_chart(fig_hosp, use_container_width=True)

    st.markdown("---")

    # Active Incident Queue Table
    st.subheader("📋 Active Emergency Incident Queue")
    inc_df = pd.DataFrame(incidents)
    display_cols = ["incident_id", "priority_category", "title", "status", "address", "victims_count", "eta_minutes"]
    st.dataframe(
        inc_df[display_cols].style.applymap(
            lambda v: 'background-color: rgba(239, 68, 68, 0.2); color: #ef4444;' if v == "CRITICAL" else
                      ('background-color: rgba(245, 158, 11, 0.2); color: #f59e0b;' if v == "URGENT" else ''),
            subset=["priority_category"]
        ),
        use_container_width=True
    )

    # Action selector to drill into Incident Details
    selected_id = st.selectbox(
        "Select Incident to Inspect Details:",
        options=[i["incident_id"] for i in incidents],
        index=0
    )
    if st.button("🔍 Open Incident Command Inspection"):
        st.session_state.selected_incident_id = selected_id
        st.session_state.current_page = "Incident Details"
        st.rerun()
