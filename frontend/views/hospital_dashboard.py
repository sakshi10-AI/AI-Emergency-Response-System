"""
Hospital Dashboard View - Regional Trauma Center Capacity & ER Matrix

Monitors hospital ICU bed capacity, trauma department availability, incoming ambulance ETAs,
and regional hospital network status.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients import hospital_client
from frontend.state_manager import refresh_hospitals


def render_hospital_dashboard_view():
    """Renders Hospital Trauma Network Dashboard page."""
    render_command_header("REGIONAL TRAUMA CENTER MATRIX", "Live ICU Bed Capacity & Emergency Department Diversion Management")

    hospitals = st.session_state.hospitals

    # Regional Metrics
    total_icu = sum(h["total_icu_beds"] for h in hospitals)
    avail_icu = sum(h["available_icu_beds"] for h in hospitals)
    avg_er_occ = sum(h["er_occupancy_percent"] for h in hospitals) // len(hospitals)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Trauma Centers", str(len(hospitals)), "Level I to III Active", "cyan")
    with c2:
        render_metric_card("Total ICU Capacity", f"{avail_icu} / {total_icu}", "Available Beds", "emerald" if avail_icu > 10 else "red")
    with c3:
        render_metric_card("Average ER Load", f"{avg_er_occ}%", "Occupancy Index", "amber")
    with c4:
        render_metric_card("Incoming Ambulances", "3 En Route", "Pre-Hospital Notifications Sent", "cyan")

    st.markdown("---")

    # Hospital Grid Cards
    st.subheader("🏥 Hospital Bed & Trauma Status Matrix")
    cols = st.columns(len(hospitals))
    for idx, hosp in enumerate(hospitals):
        with cols[idx]:
            st.markdown(f"### {hosp['name']}")
            st.markdown(f"**Level:** `{hosp['trauma_level']}` | **Status:** `{hosp['status']}`")

            progress_val = int((hosp["total_icu_beds"] - hosp["available_icu_beds"]) / hosp["total_icu_beds"] * 100)
            st.markdown(f"**ICU Occupancy ({progress_val}%):**")
            st.progress(progress_val)

            st.write(f"- **Available ICU Beds:** {hosp['available_icu_beds']} / {hosp['total_icu_beds']}")
            st.write(f"- **ER Load:** {hosp['er_occupancy_percent']}%")
            st.write(f"- **Specialties:** {', '.join(hosp['specialties'])}")

            if st.button(f"Reserve ICU Bed ({hosp['hospital_id']})"):
                result = hospital_client.reserve_icu_bed(hosp["hospital_id"])
                if result.get("status") in ("RESERVED_FALLBACK", "success"):
                    hosp["available_icu_beds"] = result.get("available_icu_beds", max(0, hosp["available_icu_beds"] - 1))
                    st.success(f"ICU Bed reserved at {hosp['name']}. Remaining: {hosp['available_icu_beds']}")
                    refresh_hospitals()
                    st.rerun()
                else:
                    st.error(result.get("message", "No available ICU beds!"))

    st.markdown("---")

    # Incoming Patient Pre-Notifications Table
    st.subheader("🚑 Incoming Patient Pre-Arrival Notifications")
    incoming_data = [
        {"Inbound Unit": "AMB-101 (Nagpur Medic 101)", "Target Hospital": "GMCH Nagpur Level I", "ETA": "4.2 mins", "Condition": "Severe Burn & Trauma", "Vitals": "BP 110/70, HR 115"},
        {"Inbound Unit": "AMB-102 (Nagpur Medic 102)", "Target Hospital": "Wockhardt Hospital Nagpur", "ETA": "6.0 mins", "Condition": "Chemical Inhalation", "Vitals": "SpO2 91%, HR 98"},
        {"Inbound Unit": "AMB-103 (Nagpur Medic 103)", "Target Hospital": "Orange City Hospital Nagpur", "ETA": "3.1 mins", "Condition": "Leg Fracture", "Vitals": "Stable, BP 120/80"}
    ]
    st.dataframe(pd.DataFrame(incoming_data), use_container_width=True)
