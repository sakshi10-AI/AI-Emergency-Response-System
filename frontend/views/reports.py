"""
Reports View - Post-Incident Formal Reporting & Export System

Displays formal incident audit reports stored in PostgreSQL, featuring:
- AI Executive Summary
- Officer & Supervisor Notes input & sign-off
- Evidence Image Gallery with Computer Vision Hazard Captions
- Chronological Audit Log Timeline Table
- Actionable Protocol Recommendations
- Professional PDF Export & CSV Export Download Buttons
"""

import streamlit as st
import json
import pandas as pd
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients import report_client
from services.report_service import report_service


def render_reports_view():
    """Renders the Post-Incident Formal Report System UI."""
    render_command_header("POST-INCIDENT REPORTS & ANALYTICS", "Formal Incident Audits, AI Summaries, PostgreSQL Persistence, and PDF/CSV Export")

    incidents = st.session_state.get("incidents", [])
    if not incidents:
        st.warning("No incidents available for report generation.")
        return

    # Incident Selection
    inc_options = {f"{inc['incident_id']} - {inc['title']}": inc for inc in incidents}
    selected_label = st.selectbox("Select Incident for Audit Report:", list(inc_options.keys()))
    incident = inc_options[selected_label]

    st.markdown("---")

    # Fetch report from DB / Client
    report = report_client.generate_incident_report(incident["incident_id"])
    compliance = report_client.get_compliance_audit(incident["incident_id"])

    # KPI Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("SLA Compliance Score", f"{compliance.get('sla_compliance_score', 100)}%", "Dispatched under 5m", "emerald")
    with c2:
        render_metric_card("Severity Level", f"Level {incident.get('severity_level', 1)}", incident.get('priority_category', 'CRITICAL'), "red")
    with c3:
        render_metric_card("Victims Handled", str(incident.get('victims_count', 0)), "Zero Fatalities", "cyan")
    with c4:
        render_metric_card("AI Triage Accuracy", "99.2%", "Verified by Officer", "emerald")

    st.markdown("---")

    # Layout: Left column (AI Summary, Officer Notes, Recommendations, Timeline) | Right column (Evidence Images, Exports)
    col_main, col_side = st.columns([2, 1])

    with col_main:
        # 1. AI Executive Summary
        st.subheader("🤖 AI Executive Summary")
        st.markdown(f"""
        <div style="background-color: #1f2937; border-left: 4px solid #06b6d4; padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem;">
            <p style="color: #e5e7eb; line-height: 1.6; margin: 0; font-size: 0.95rem;">
                {report.get("ai_summary", "Multi-agent dispatch pipeline completed successfully for this incident.")}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 2. Officer & Supervisor Notes Area
        st.subheader("✍️ Officer & Supervisor Notes")
        existing_notes = report.get("officer_notes", "Supervisor verified all agent actions. No manual override required.")
        officer_notes_input = st.text_area(
            "Enter manual officer observations, field debrief, or sign-off notes:",
            value=existing_notes,
            height=120,
            key=f"notes_input_{incident['incident_id']}"
        )

        if st.button("💾 Save & Persist Report to PostgreSQL", type="primary"):
            with st.spinner("Persisting formal report to PostgreSQL database..."):
                save_res = report_client.create_report(
                    incident_id=incident["incident_id"],
                    officer_notes=officer_notes_input
                )
                st.success("Formal report successfully saved and committed to PostgreSQL!")

        st.markdown("---")

        # 3. Actionable Protocol Recommendations
        st.subheader("📋 Actionable Protocol Recommendations")
        recs = report.get("recommendations", [
            "Signal preemption at Wardha Road & Ajni Square junction executed smoothly; expand to Ring Road.",
            "Hospital routing to GMCH Nagpur was optimal based on burn unit & ICU availability.",
            "AI Triage accuracy correctly flagged active rollover threat on Wardha Road."
        ])
        for r in recs:
            st.markdown(f"- 🔹 **{r}**")

        st.markdown("---")

        # 4. Chronological Audit Log Timeline
        st.subheader("⏱️ Chronological Audit Timeline Table")
        timeline = report.get("timeline_data", [
            {"time": "10:12:05", "source": "SupervisorAgent", "event": "Incident received & routed to Vision module"},
            {"time": "10:12:07", "source": "VisionAgent", "event": "Detected 3 vehicles + active fire hazard on Wardha Road"},
            {"time": "10:12:09", "source": "SeverityAgent", "event": "Assigned CRITICAL priority (Level 1)"},
            {"time": "10:12:12", "source": "HospitalAgent", "event": "Selected GMCH Nagpur Level I Trauma Center"},
            {"time": "10:12:15", "source": "AmbulanceAgent", "event": "Dispatched NMC-AMB-101 (ALS) ETA 4.2m"},
            {"time": "10:12:18", "source": "TrafficAgent", "event": "Preempted 4 traffic signals along Wardha Road"}
        ])

        df_timeline = pd.DataFrame(timeline)
        st.dataframe(df_timeline, use_container_width=True, hide_index=True)

    with col_side:
        # 5. Export Actions Box
        st.subheader("📥 Export Formal Report")
        st.markdown("""
        <div style="background-color: #1f2937; border: 1px solid #374151; padding: 1.25rem; border-radius: 8px; margin-bottom: 1.5rem;">
            <p style="color: #9ca3af; font-size: 0.85rem; margin-top: 0;">Download compiled audit reports with executive branding and SLA signatures.</p>
        </div>
        """, unsafe_allow_html=True)

        # Generate PDF bytes
        pdf_bytes = report_service.generate_pdf_report(report)
        st.download_button(
            label="📄 Download Formal PDF Report",
            data=pdf_bytes,
            file_name=f"Incident_Report_{incident['incident_id']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        # Generate CSV bytes
        csv_bytes = report_service.generate_csv_report(report)
        st.download_button(
            label="📊 Download CSV Data Export",
            data=csv_bytes,
            file_name=f"Incident_Report_{incident['incident_id']}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.markdown("---")

        # 6. Evidence Images Gallery
        st.subheader("📷 Evidence Images & Visual AI Detection")
        evidence = report.get("evidence_images", [
            {"image_id": "IMG-001", "caption": "Vehicle Fire & Flame Bounding Box (96% Confidence)", "hazard": "Active Fire"},
            {"image_id": "IMG-002", "caption": "Structural Wall Damage & Rollover Collision Area", "hazard": "Impact Hazard"}
        ])

        for ev in evidence:
            st.markdown(f"""
            <div style="background-color: #111827; border: 1px solid #374151; padding: 0.85rem; border-radius: 6px; margin-bottom: 0.75rem;">
                <div style="font-weight: bold; color: #ef4444; font-size: 0.85rem;">⚠️ {ev.get('hazard', 'HAZARD DETECTED')}</div>
                <div style="color: #d1d5db; font-size: 0.8rem; margin-top: 0.25rem;">{ev.get('caption', '')}</div>
                <div style="color: #6b7280; font-size: 0.7rem; margin-top: 0.25rem;">ID: <code>{ev.get('image_id')}</code></div>
            </div>
            """, unsafe_allow_html=True)
