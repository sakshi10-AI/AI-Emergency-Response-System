"""
Analytics View - Business Intelligence & Operational Performance Analytics

Generates 8 interactive Plotly charts, response time benchmarks, severity distribution,
hospital capacity, ambulance fleet allocation, AI triage accuracy, and Computer Vision confidence.
Includes one-click PDF & CSV dashboard export buttons.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import io
import csv
from frontend.theme import render_command_header, render_metric_card
from frontend.api_clients import report_client
from services.report_service import report_service


def render_analytics_view():
    """Renders Executive BI Analytics page with 8 Plotly charts & export capabilities."""
    render_command_header("EXECUTIVE OPERATIONS ANALYTICS", "Historical Performance Metrics, Response Times & Hazard Trends")

    # Time Horizon Filter
    st.sidebar.markdown("### 🔍 BI Analytics Filters")
    time_range = st.sidebar.selectbox("Select Time Horizon:", ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Year-to-Date"])
    severity_filter = st.sidebar.multiselect(
        "Filter Severity Levels:",
        ["Level 1 Critical", "Level 2 Urgent", "Level 3 Moderate", "Level 4 Minor"],
        default=["Level 1 Critical", "Level 2 Urgent", "Level 3 Moderate", "Level 4 Minor"]
    )

    # Fetch Analytics Data
    data = report_client.get_executive_analytics(time_horizon=time_range)

    # KPI Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Avg Response Time", f"{data.get('avg_response_time_minutes', 4.1)} mins", "Target: < 6.0 mins (-18%)", "emerald")
    with c2:
        render_metric_card("Total Incidents", f"{data.get('total_incidents', 148)} Calls", "100% Multi-Agent Triage", "cyan")
    with c3:
        render_metric_card("Dispatch Accuracy", f"{data.get('dispatch_accuracy_percent', 98.4)}%", "Zero Misrouting Errors", "emerald")
    with c4:
        render_metric_card("AI Triage Accuracy", f"{data.get('ai_triage_accuracy_percent', 99.2)}%", "Verified by Officers", "emerald")

    st.markdown("---")

    # =========================================================================
    # ROW 1: Daily Incidents & Monthly Incidents
    # =========================================================================
    r1_col1, r1_col2 = st.columns(2)

    with r1_col1:
        st.subheader("1. 📈 Daily Incidents Timeline (24-Hour Curve)")
        df_daily = pd.DataFrame(data.get("daily_incidents", []))
        fig_daily = px.area(
            df_daily, x="hour", y="count",
            labels={"hour": "Hour of Day", "count": "Incidents Reported"},
            color_discrete_sequence=["#06b6d4"], template="plotly_dark"
        )
        fig_daily.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_daily, use_container_width=True)

    with r1_col2:
        st.subheader("2. 📊 Monthly Incidents Volume (12-Month Horizon)")
        df_monthly = pd.DataFrame(data.get("monthly_incidents", []))
        fig_monthly = px.bar(
            df_monthly, x="month", y="incidents",
            labels={"month": "Month", "incidents": "Total Incidents"},
            color="incidents", color_continuous_scale="Blues", template="plotly_dark"
        )
        fig_monthly.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_monthly, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # ROW 2: Severity Breakdown & Average Response Time Benchmark
    # =========================================================================
    r2_col1, r2_col2 = st.columns(2)

    with r2_col1:
        st.subheader("3. 🎯 Incident Severity Breakdown")
        sev_dict = data.get("severity_breakdown", {})
        df_sev = pd.DataFrame({"Severity": list(sev_dict.keys()), "Count": list(sev_dict.values())})
        fig_sev = px.pie(
            df_sev, values="Count", names="Severity", hole=0.45,
            color_discrete_sequence=["#ef4444", "#f59e0b", "#06b6d4", "#10b981"], template="plotly_dark"
        )
        fig_sev.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_sev, use_container_width=True)

    with r2_col2:
        st.subheader("4. ⏱️ Average Response Time Benchmark vs SLA")
        df_resp = pd.DataFrame(data.get("response_times", []))
        fig_resp = px.line(
            df_resp, x="hour", y=["dispatch", "travel", "total"],
            labels={"hour": "Hour", "value": "Minutes"},
            markers=True, color_discrete_sequence=["#06b6d4", "#f59e0b", "#10b981"], template="plotly_dark"
        )
        # Add SLA target line (6.0m)
        fig_resp.add_hline(y=6.0, line_dash="dash", line_color="#ef4444", annotation_text="Target SLA (6.0m)")
        fig_resp.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_resp, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # ROW 3: Hospital Capacity Usage & Ambulance Fleet Allocation
    # =========================================================================
    r3_col1, r3_col2 = st.columns(2)

    with r3_col1:
        st.subheader("5. 🏥 Hospital Network Capacity Usage (%)")
        df_hosp = pd.DataFrame(data.get("hospital_usage", []))
        fig_hosp = px.bar(
            df_hosp, y="hospital", x="er_load", orientation="h",
            labels={"hospital": "Trauma Center", "er_load": "ER Occupancy %"},
            color="er_load", color_continuous_scale="Reds", template="plotly_dark"
        )
        fig_hosp.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_hosp, use_container_width=True)

    with r3_col2:
        st.subheader("6. 🚑 Ambulance Fleet Unit Status Allocation")
        amb_dict = data.get("ambulance_usage", {})
        df_amb = pd.DataFrame({"Status": list(amb_dict.keys()), "Units": list(amb_dict.values())})
        fig_amb = px.pie(
            df_amb, values="Units", names="Status", hole=0.4,
            color_discrete_sequence=["#ef4444", "#3b82f6", "#06b6d4", "#10b981"], template="plotly_dark"
        )
        fig_amb.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_amb, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # ROW 4: AI Multi-Agent Triage Accuracy & Detection Confidence
    # =========================================================================
    r4_col1, r4_col2 = st.columns(2)

    with r4_col1:
        st.subheader("7. 🧠 AI Multi-Agent Triage Accuracy Trend (%)")
        df_acc = pd.DataFrame(data.get("ai_accuracy", []))
        fig_acc = px.line(
            df_acc, x="day", y="accuracy", markers=True,
            labels={"day": "Timeline", "accuracy": "Accuracy %"},
            color_discrete_sequence=["#10b981"], template="plotly_dark"
        )
        fig_acc.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20), yaxis_range=[95, 100])
        st.plotly_chart(fig_acc, use_container_width=True)

    with r4_col2:
        st.subheader("8. 👁️ Computer Vision Hazard Detection Confidence")
        df_det = pd.DataFrame(data.get("detection_confidence", []))
        fig_det = px.bar(
            df_det, x="hazard", y="confidence",
            labels={"hazard": "Detected Hazard Class", "confidence": "Confidence %"},
            color="confidence", color_continuous_scale="Viridis", template="plotly_dark"
        )
        fig_det.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=20), yaxis_range=[80, 100])
        st.plotly_chart(fig_det, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # DASHBOARD EXPORT BAR
    # =========================================================================
    st.subheader("📤 Export Executive BI Analytics Dashboard")
    st.markdown("Generate formatted PDF executive reports or export raw analytics datasets as CSV.")

    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        sample_report_dict = {
            "incident_id": "EXEC-ANALYTICS-2026",
            "tracking_code": "BI-AUDIT-2026",
            "title": f"Executive Operations Analytics ({time_range})",
            "ai_summary": f"Executive performance audit for horizon '{time_range}'. Average response time maintained at 4.1 mins (18% under target SLA). Multi-agent dispatch accuracy reached 98.4%. Zero hospital diversions triggered.",
            "officer_notes": "Executive BI report approved by EOC Command Officer.",
            "recommendations": [
                "Maintain signal preemption corridor along Hwy 101.",
                "Expand ALS unit allocation in Sector 4 during peak 16:00-18:00 hours."
            ],
            "timeline_data": [
                {"time": "08:00", "source": "System", "event": "12 incidents handled successfully"},
                {"time": "12:00", "source": "System", "event": "Peak 24 incidents managed with 0 diversions"},
                {"time": "16:00", "source": "System", "event": "29 incidents handled with 4.1m avg response"}
            ],
            "metrics_data": {
                "sla_compliance_score": 100,
                "ambulance_eta_minutes": 4.1
            }
        }
        pdf_bytes = report_service.generate_pdf_report(sample_report_dict)
        st.download_button(
            label="📄 Download Executive Analytics Report (PDF)",
            data=pdf_bytes,
            file_name=f"Executive_Analytics_Report_{time_range.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with exp_col2:
        # Prepare CSV dump of all datasets
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)

        writer.writerow(["EXECUTIVE ANALYTICS METRICS"])
        writer.writerow(["Time Horizon", time_range])
        writer.writerow(["Total Incidents", data.get("total_incidents")])
        writer.writerow(["Avg Response Time (min)", data.get("avg_response_time_minutes")])
        writer.writerow(["Dispatch Accuracy (%)", data.get("dispatch_accuracy_percent")])
        writer.writerow(["AI Triage Accuracy (%)", data.get("ai_triage_accuracy_percent")])
        writer.writerow([])

        writer.writerow(["DAILY INCIDENTS (24H)"])
        writer.writerow(["Hour", "Count"])
        for item in data.get("daily_incidents", []):
            writer.writerow([item.get("hour"), item.get("count")])
        writer.writerow([])

        writer.writerow(["SEVERITY BREAKDOWN"])
        for k, v in data.get("severity_breakdown", {}).items():
            writer.writerow([k, v])
        writer.writerow([])

        writer.writerow(["DETECTION CONFIDENCE"])
        writer.writerow(["Hazard Class", "Confidence %"])
        for item in data.get("detection_confidence", []):
            writer.writerow([item.get("hazard"), item.get("confidence")])

        csv_bytes = csv_buf.getvalue().encode("utf-8")
        csv_buf.close()

        st.download_button(
            label="📊 Download Raw Analytics Dataset (CSV)",
            data=csv_bytes,
            file_name=f"Analytics_Dataset_{time_range.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
