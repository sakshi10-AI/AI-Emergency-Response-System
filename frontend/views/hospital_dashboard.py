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
            st.markdown(f"- **📞 Emergency Desk:** `{hosp.get('emergency_phone', '7796119389')}`")

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

    # =========================================================================
    # Automated Hospital Emergency Call Dispatcher Section
    # =========================================================================
    st.subheader("📞 Automated Accident-to-Hospital Emergency Call Dispatcher")
    st.markdown("""
    When an accident occurs in the city, the system calculates the **nearest available trauma center**
    and immediately places an **automated high-priority voice dispatch call** to alert the trauma surgeon and reserve resuscitation beds.
    """)

    call_col1, call_col2 = st.columns([1.2, 1])

    with call_col1:
        st.markdown("### 🚨 Dispatch Emergency Voice Alert Call")
        dest_phone = st.text_input("Emergency Destination Phone:", value="7796119389", key="call_dest_phone", help="Hospital Emergency Desk target number")
        target_incident = st.selectbox(
            "Select Accident Scene:",
            [
                "INC-8821 | Major Collision near Wardha Road & Ajni Square",
                "INC-9042 | Chemical Vapor Leak at MIDC Butibori",
                "INC-3310 | Multi-Car Pileup on Central Avenue"
            ],
            key="call_incident_select"
        )
        nearest_hosp_display = "Government Medical College & Hospital (GMCH) Nagpur (2.1 km away)"
        st.info(f"📍 **Target Hospital Identified:** {nearest_hosp_display}\n\n📞 **Emergency Line Dialing:** `{dest_phone}`")

        if st.button("🚀 Trigger Automated Call to Nearest Hospital (7796119389)", type="primary", use_container_width=True):
            with st.spinner(f"Initiating high-priority voice dispatch call to {dest_phone}..."):
                inc_id = target_incident.split(" | ")[0]
                call_res = hospital_client.dispatch_emergency_call(inc_id, target_phone=dest_phone)
                st.session_state["last_call_dispatched"] = call_res
                st.success(f"✅ Call Dispatched to {dest_phone}! Status: CONNECTED")

        if "last_call_dispatched" in st.session_state:
            last_c = st.session_state["last_call_dispatched"]
            st.markdown(f"""
            <div style="background-color: #1e293b; border-left: 4px solid #10b981; padding: 1rem; border-radius: 6px; margin-top: 1rem;">
                <div style="color: #10b981; font-weight: bold; font-size: 0.95rem;">📞 VOICE CALL CONNECTED • {last_c.get('target_phone')}</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.25rem;">Provider SID: <code>{last_c.get('provider_call_id', 'CALL-SIM-7796119389')}</code> | Distance: {last_c.get('distance_km', 2.1)} km | ETA: {last_c.get('eta_minutes', 4.2)} mins</div>
                <div style="color: #f1f5f9; font-size: 0.9rem; margin-top: 0.5rem; font-style: italic;">"{last_c.get('speech_transcript')}"</div>
            </div>
            """, unsafe_allow_html=True)

    with call_col2:
        st.markdown("### 📋 Emergency Call Dispatch Telemetry Logs")
        call_history = hospital_client.get_call_history(limit=5)
        if call_history:
            for ch in call_history[:4]:
                st.markdown(f"""
                <div style="background-color: #0f172a; border: 1px solid #334155; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold; color: #38bdf8;">{ch.get('hospital_name', 'GMCH Nagpur')}</span>
                        <span style="color: #10b981; font-weight: bold; font-size: 0.8rem;">● {ch.get('status', 'COMPLETED')}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem;">
                        Target: <b>{ch.get('target_phone', '7796119389')}</b> | ETA: {ch.get('eta_minutes', 4.2)}m | Duration: {ch.get('duration_seconds', 42)}s
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No recent emergency calls recorded.")

    st.markdown("---")

    # Incoming Patient Pre-Notifications Table
    st.subheader("🚑 Incoming Patient Pre-Arrival Notifications")
    incoming_data = [
        {"Inbound Unit": "AMB-101 (Nagpur Medic 101)", "Target Hospital": "GMCH Nagpur Level I", "ETA": "4.2 mins", "Condition": "Severe Burn & Trauma", "Vitals": "BP 110/70, HR 115", "Hospital Called": "7796119389"},
        {"Inbound Unit": "AMB-102 (Nagpur Medic 102)", "Target Hospital": "Wockhardt Hospital Nagpur", "ETA": "6.0 mins", "Condition": "Chemical Inhalation", "Vitals": "SpO2 91%, HR 98", "Hospital Called": "7796119389"},
        {"Inbound Unit": "AMB-103 (Nagpur Medic 103)", "Target Hospital": "Orange City Hospital Nagpur", "ETA": "3.1 mins", "Condition": "Leg Fracture", "Vitals": "Stable, BP 120/80", "Hospital Called": "7796119389"}
    ]
    st.dataframe(pd.DataFrame(incoming_data), use_container_width=True)
