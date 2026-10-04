"""
Upload Video View - Drone & Citizen Video Scene Analysis

Ingests emergency video footage and performs multi-frame temporal consistency,
persistence voting, keyframe extraction, and automated hospital call alerting (7796119389).
"""

import asyncio
import io
import streamlit as st
import time
from PIL import Image
import base64

from frontend.theme import render_command_header, render_metric_card
from vision.service import vision_detection_service
from services.hospital_call_service import hospital_call_service
from database.connection import AsyncSessionLocal


def render_upload_video_view():
    """Renders Video Analysis Upload page."""
    render_command_header(
        "DRONE & FIELD VIDEO ANALYSIS",
        "Temporal Consistency, Keyframe Anomaly Detection & Automated Hospital Alerting"
    )

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("📹 Video Footage Uploader")
        uploaded_file = st.file_uploader(
            "Drag & Drop Emergency Video (.mp4, .avi, .mov)",
            type=["mp4", "avi", "mov"]
        )

        sample_rate = st.slider("Sampling Interval (Seconds per Keyframe)", min_value=0.5, max_value=3.0, value=1.0, step=0.5)

        if uploaded_file is not None:
            video_bytes = uploaded_file.getvalue()
            st.video(video_bytes)
            st.success(f"Video '{uploaded_file.name}' loaded ({len(video_bytes) // 1024} KB).")

            run_video = st.button("⚡ Run Temporal Video Analysis Engine", type="primary", use_container_width=True)
        else:
            st.info("Upload emergency drone, CCTV, or smartphone video footage above to test real temporal triage.")
            run_video = False

    with col2:
        st.subheader("🤖 AI Temporal Vision Report")

        if run_video or "last_video_analysis" in st.session_state:
            if run_video:
                with st.spinner("Extracting keyframes and executing multi-frame persistence voting..."):
                    try:
                        res = asyncio.run(
                            vision_detection_service.analyze_video_temporal(
                                video_input=video_bytes,
                                sample_interval_sec=sample_rate
                            )
                        )
                        st.session_state["last_video_analysis"] = res
                    except Exception as e:
                        st.error(f"Video analysis error: {e}")
                        return

            res = st.session_state.get("last_video_analysis")
            if res:
                fire_text = "CONFIRMED (Persistent)" if res.fire_confirmed else "No Active Fire"
                fire_color = "red" if res.fire_confirmed else "green"

                render_metric_card("Overall Severity Score", f"{res.overall_severity_score} / 100", f"Triage Tier: {res.overall_severity_level}", "red" if res.overall_severity_score >= 70 else "amber")
                render_metric_card("Fire Hazard Persistence", fire_text, f"Frames sampled: {res.total_frames_sampled}", fire_color)
                render_metric_card("Max Vehicles Involved", f"{res.max_vehicle_count} Vehicle(s)", "Peak traffic density", "amber")
                render_metric_card("Estimated Casualties", f"{res.trapped_victims_estimated} Person(s)", "Immediate EMS required", "red" if res.trapped_victims_estimated > 0 else "cyan")
        else:
            st.info("Awaiting video upload and analysis.")

    # Lower Section: Timeline & Keyframe Gallery & Hospital Call
    if "last_video_analysis" in st.session_state:
        res = st.session_state["last_video_analysis"]

        st.markdown("---")
        t_col, h_col = st.columns([1.3, 1])

        with t_col:
            st.markdown("### 🔍 Chronological Timeline Breakdown (Multi-Frame Persistence)")
            if res.timeline_events:
                for ev in res.timeline_events:
                    st.markdown(
                        f"- **{ev.timestamp_range}** | `{ev.hazard_type}` ({int(ev.confidence * 100)}%): "
                        f"{ev.description} — *Severity: {ev.severity_level}*"
                    )
            else:
                st.write("No distinct temporal anomalies detected.")

            st.markdown("### 📋 Recommended Triage Dispatch")
            st.warning(res.triage_dispatch_recommendation)

        with h_col:
            st.markdown("### 🚨 Emergency Hospital Alerting")
            st.write(f"Target Desk: **`{res.target_hospital_phone}`**")

            call_btn = st.button("📞 Dispatch Automated Call to Nearest Hospital (7796119389)", key="video_call_btn", type="secondary", use_container_width=True)
            if call_btn:
                with st.spinner("Dispatching emergency call to trauma center..."):
                    async def _trigger_call():
                        async with AsyncSessionLocal() as db:
                            return await hospital_call_service.dispatch_nearest_hospital_call(
                                db=db,
                                accident_lat=21.1458,
                                accident_lon=79.0882,
                                incident_type="VIDEO_CONFIRMED_COLLISION",
                                severity_score=res.overall_severity_score,
                                casualties=max(res.trapped_victims_estimated, 1),
                                summary=res.triage_dispatch_recommendation,
                                target_phone_override="7796119389"
                            )

                    try:
                        call_res = asyncio.run(_trigger_call())
                        st.success(f"✅ Call Dispatched to **{call_res.hospital_name}** at `{call_res.target_phone}`!")
                        st.info(f"**Distance:** {call_res.distance_km} km | **ETA:** {call_res.estimated_arrival_minutes} mins")
                        with st.expander("🔊 Spoken Clinical Transcript"):
                            st.code(call_res.speech_transcript, language="text")
                    except Exception as e:
                        st.error(f"Failed to place call: {e}")

        # Keyframe Thumbnails
        if res.keyframe_samples:
            st.markdown("---")
            st.markdown("### 🎞️ Sampled Keyframe Annotations")
            cols = st.columns(len(res.keyframe_samples))
            for i, kf in enumerate(res.keyframe_samples):
                with cols[i]:
                    img_data = base64.b64decode(kf["thumbnail_base64"])
                    st.image(Image.open(io.BytesIO(img_data)), caption=f"Time {kf['timestamp']} [{kf['severity']}]", use_container_width=True)
