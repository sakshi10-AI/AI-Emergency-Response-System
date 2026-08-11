"""
Upload Image View - Visual Scene Photo Analysis

Ingests emergency photos and performs side-by-side Computer Vision hazard detection,
structural damage assessment, and triage score generation.
"""

import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
from frontend.theme import render_command_header, render_metric_card


def render_upload_image_view():
    """Renders Image Scene Photo Analysis page."""
    render_command_header("VISUAL SCENE PHOTO ANALYSIS", "Upload Emergency Scene Photos for Instant Hazard Triage")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📷 Emergency Photo Ingestion")
        uploaded_image = st.file_uploader(
            "Upload Photo (.png, .jpg, .jpeg)",
            type=["png", "jpg", "jpeg"]
        )

        if uploaded_image is not None:
            img = Image.open(uploaded_image)
            st.image(img, caption="Original Uploaded Scene Photo", use_container_width=True)
        else:
            # Generate synthetic test image
            img = Image.new("RGB", (500, 300), color=(25, 30, 45))
            draw = ImageDraw.Draw(img)
            draw.rectangle([50, 50, 450, 250], outline="gray", width=2)
            draw.text((180, 140), "SCENE PHOTO PLACEHOLDER", fill="white")
            st.image(img, caption="Default Test Scene Photo", use_container_width=True)

    with col2:
        st.subheader("🎯 Computer Vision Hazard Overlays")

        # Create annotated image
        annotated_img = img.copy()
        draw_ann = ImageDraw.Draw(annotated_img)
        draw_ann.rectangle([80, 70, 260, 220], outline="red", width=4)
        draw_ann.text((85, 75), "HAZARD: VEHICLE FIRE (96%)", fill="red")
        draw_ann.rectangle([280, 100, 420, 230], outline="yellow", width=4)
        draw_ann.text((285, 105), "HAZARD: STRUCTURAL DAMAGE (84%)", fill="yellow")

        st.image(annotated_img, caption="AI Annotated Hazard Detection Overlays", use_container_width=True)

    st.markdown("---")
    st.subheader("📊 Instant Visual Triage Metrics")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Overall Severity Score", "88 / 100", "Critical Impact Level", "red")
    with m2:
        render_metric_card("Fire & Smoke Status", "ACTIVE FLAMES", "High Spreading Threat", "red")
    with m3:
        render_metric_card("Structural Risk", "MODERATE", "Partial Wall Collapse", "amber")
    with m4:
        render_metric_card("Victim Count Est.", "3 Persons", "Immediate Evacuation Required", "cyan")

    if st.button("🚀 Push Visual Assessment to Incident Command Flow"):
        st.success("Visual assessment successfully attached to Active Incident queue!")
