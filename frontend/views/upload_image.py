"""
Upload Image View - Multimodal VLM Visual Scene Analysis

Ingests emergency photos and performs Multimodal Vision-Language Model (VLM)
hazard comprehension, vehicle deformation assessment, quality gate validation,
and automated hospital call alerting to trauma desks (target: 7796119389).
"""

import asyncio
import base64
import io
import streamlit as st
import numpy as np
from PIL import Image

from frontend.theme import render_command_header, render_metric_card
from vision.service import vision_detection_service
from services.hospital_call_service import hospital_call_service
from database.connection import AsyncSessionLocal


def render_upload_image_view():
    """Renders Image Scene Photo Analysis page."""
    render_command_header(
        "VISUAL SCENE PHOTO ANALYSIS",
        "Multimodal VLM Hazard Triage & Automated Hospital Call Routing"
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📷 Emergency Photo Ingestion")
        uploaded_image = st.file_uploader(
            "Upload Emergency Photo (.png, .jpg, .jpeg)",
            type=["png", "jpg", "jpeg"]
        )

        prompt_hint = st.text_input(
            "Scene Context / Caller Details (Optional)",
            placeholder="e.g. 2-car collision on Wardha Road with smoke observed"
        )

        if uploaded_image is not None:
            image_bytes = uploaded_image.getvalue()
            img = Image.open(io.BytesIO(image_bytes))
            st.image(img, caption=f"Original Photo: {uploaded_image.name} ({img.width}x{img.height})", use_container_width=True)
        else:
            # Generate default scene sample for immediate testing
            img = Image.new("RGB", (640, 480), color=(30, 35, 50))
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            image_bytes = buf.getvalue()
            st.image(img, caption="Default Test Canvas (Upload a photo above to test)", use_container_width=True)

        run_analysis = st.button("🔍 Run Multimodal VLM Scene Analysis", type="primary", use_container_width=True)

    with col2:
        st.subheader("🎯 AI Vision Overlays & Clinical Triage")

        if run_analysis or "last_image_analysis" in st.session_state:
            if run_analysis:
                with st.spinner("Analyzing scene via Gemini Vision VLM & Quality Gate..."):
                    try:
                        analysis, annotated_b64 = asyncio.run(
                            vision_detection_service.analyze_image_vlm(
                                image_source=image_bytes,
                                prompt_hint=prompt_hint,
                                draw_annotations=True
                            )
                        )
                        st.session_state["last_image_analysis"] = analysis
                        st.session_state["last_annotated_b64"] = annotated_b64
                    except Exception as e:
                        st.error(f"Inference error: {e}")
                        return

            analysis = st.session_state.get("last_image_analysis")
            annotated_b64 = st.session_state.get("last_annotated_b64")

            if annotated_b64:
                ann_bytes = base64.b64decode(annotated_b64)
                ann_img = Image.open(io.BytesIO(ann_bytes))
                st.image(ann_img, caption=f"Dynamic AI Hazard Overlays ({analysis.model_provider})", use_container_width=True)
            else:
                st.info("No annotations available.")

            # Quality gate badge
            q_stat = analysis.quality_status if hasattr(analysis, "quality_status") else {}
            if q_stat and q_stat.get("quality_tier") != "OPTIMAL":
                st.warning(f"⚠️ Quality Advisory: {q_stat.get('advisory')} (Blur: {q_stat.get('blur_score')})")
            else:
                st.success("✅ Visual Quality Optimal (Laplacian Blur Check Passed)")
        else:
            st.info("Upload an image and click 'Run Multimodal VLM Scene Analysis' to generate real-time hazard detection overlays.")

    # Bottom Triage Section
    if "last_image_analysis" in st.session_state:
        analysis = st.session_state["last_image_analysis"]

        st.markdown("---")
        st.subheader("📊 Instant Visual Triage Metrics")
        m1, m2, m3, m4 = st.columns(4)

        score_color = "red" if analysis.severity_score >= 75 else ("amber" if analysis.severity_score >= 50 else "cyan")
        fire_str = "ACTIVE FLAMES" if analysis.fire_detected else ("SMOKE HAZE" if analysis.smoke_detected else "CLEAR")
        fire_color = "red" if analysis.fire_detected else ("amber" if analysis.smoke_detected else "green")

        with m1:
            render_metric_card("Overall Severity Score", f"{analysis.severity_score} / 100", f"Tier: {analysis.severity_level}", score_color)
        with m2:
            render_metric_card("Fire & Smoke Status", fire_str, analysis.fire_details or analysis.smoke_details or "No active combustion", fire_color)
        with m3:
            render_metric_card("Vehicles Involved", f"{analysis.vehicles_involved_count} Unit(s)", analysis.collision_type or "Stationary vehicles", "amber")
        with m4:
            render_metric_card("Victim Count Est.", f"{analysis.victims_count_est} Person(s)", "Trapped / Medical Attention", "red" if analysis.victims_count_est > 0 else "cyan")

        # Clinical Summary & Recommended Dispatch
        col_summary, col_call = st.columns([1.2, 1])
        with col_summary:
            st.markdown(f"**Scene Clinical Summary:** {analysis.scene_summary}")
            st.markdown(f"**Recommended Dispatch:** `{analysis.triage_recommendation}`")

        with col_call:
            st.markdown("### 🚨 Emergency Hospital Alerting")
            st.write(f"Target Trauma Desk: **`7796119389`**")

            call_btn = st.button("📞 Dispatch Automated Call to Nearest Hospital (7796119389)", type="secondary", use_container_width=True)
            if call_btn:
                with st.spinner("Connecting to nearest trauma center via telephony gateway..."):
                    async def _trigger_call():
                        async with AsyncSessionLocal() as db:
                            return await hospital_call_service.dispatch_nearest_hospital_call(
                                db=db,
                                accident_lat=21.1458,
                                accident_lon=79.0882,
                                incident_type=analysis.collision_type or "VEHICLE_COLLISION",
                                severity_score=analysis.severity_score,
                                casualties=max(analysis.victims_count_est, 1),
                                summary=analysis.scene_summary,
                                target_phone_override="7796119389"
                            )

                    try:
                        call_res = asyncio.run(_trigger_call())
                        st.success(f"✅ Call Dispatched to **{call_res.hospital_name}** at `{call_res.target_phone}`!")
                        st.info(f"**Distance:** {call_res.distance_km} km | **ETA:** {call_res.estimated_arrival_minutes} mins | **Status:** {call_res.call_status}")
                        with st.expander("🔊 Spoken Clinical Audio Transcript"):
                            st.code(call_res.speech_transcript, language="text")
                    except Exception as e:
                        st.error(f"Failed to place call: {e}")
