"""
Live Camera View - Real-Time Surveillance & Computer Vision Grid

Provides real-time camera grid feeds, automated computer vision hazard alerts,
and camera control simulations for the EOC.
"""

import streamlit as st
import numpy as np
from frontend.theme import render_command_header, render_metric_card


def render_live_camera_view():
    """Renders Live Camera Surveillance Matrix page."""
    render_command_header("LIVE SURVEILLANCE CAMERA MATRIX", "AI-Powered Computer Vision & Field Camera Feed Stream")

    cameras = st.session_state.camera_streams

    # Stream status metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Total Feeds", str(len(cameras)), "Connected CCTV & Drones", "cyan")
    with col2:
        render_metric_card("Active Alerts", "2 Feeds", "Hazard Detected", "red")
    with col3:
        render_metric_card("AI Detection Latency", "42 ms", "Real-Time OpenCV/YOLO", "emerald")
    with col4:
        render_metric_card("Stream Health", "100%", "Zero Frame Loss", "amber")

    st.markdown("---")

    # Camera Feed Grid (2x2 Grid)
    grid_col1, grid_col2 = st.columns(2)

    for idx, cam in enumerate(cameras):
        col = grid_col1 if idx % 2 == 0 else grid_col2
        with col:
            status_color = "🔴 ALERT" if cam["status"] == "ALERT" else ("🟡 WARNING" if cam["status"] == "WARNING" else "🟢 ONLINE")
            st.markdown(f"### 📹 {cam['cam_id']} - {cam['location']} [{status_color}]")

            # Simulated Camera Feed Placeholder
            img_array = np.zeros((240, 420, 3), dtype=np.uint8)
            img_array[:, :] = [18, 25, 38]  # Dark cyber background

            # Draw simulated bounding box if alert
            if cam["status"] == "ALERT":
                img_array[60:180, 100:300] = [180, 40, 40]  # Red hazard box
            elif cam["status"] == "WARNING":
                img_array[80:160, 120:280] = [180, 140, 40]  # Amber box

            st.image(img_array, caption=f"Feed: {cam['cam_id']} | Resolution: 1080p60 | Hazards: {', '.join(cam['hazards_detected'])}", use_container_width=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.button(f"🔍 Zoom {cam['cam_id']}", key=f"zoom_{cam['cam_id']}")
            with c2:
                st.button(f"🔄 PTZ Pan", key=f"pan_{cam['cam_id']}")
            with c3:
                st.button(f"🚨 Trigger Alert", key=f"alert_{cam['cam_id']}")
            st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚙️ Pan-Tilt-Zoom (PTZ) & Stream Controls")
    sel_cam = st.selectbox("Select Target Stream for Manual PTZ Control:", [c["cam_id"] for c in cameras])
    st.slider("Pan Angle", -180, 180, 0, key="pan_slider")
    st.slider("Tilt Angle", -90, 90, 15, key="tilt_slider")
    st.slider("Optical Zoom Level", 1, 20, 4, key="zoom_slider")
    if st.button("Apply PTZ Orientation"):
        st.success(f"PTZ orientation updated for stream {sel_cam}.")
