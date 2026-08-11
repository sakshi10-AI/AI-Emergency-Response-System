"""
Live Webcam AI Analysis View — Nagpur EOC

Captures frames from the laptop's built-in webcam (Camera 0) and passes them
through the YOLOv11 computer vision pipeline in real-time.

Detected hazards (accidents, fires, vehicles) automatically trigger the EOC
incident creation workflow with Nagpur-specific dispatch recommendations.
"""

import sys
import time
import uuid
import datetime
from pathlib import Path

# Ensure project root is on sys.path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from frontend.theme import render_command_header, render_metric_card


# ─────────────────────────── colour palette ────────────────────────────────
CATEGORY_COLOURS = {
    "accident":   (239, 68,  68),   # red-500
    "fire":       (249, 115, 22),   # orange-500
    "smoke":      (148, 163, 184),  # slate-400
    "vehicle":    (34,  211, 238),  # cyan-400
    "pedestrian": (167, 243, 208),  # emerald-200
    "hazard":     (250, 204, 21),   # yellow-400
}

PRIORITY_MAP = {
    "accident": ("CRITICAL", 1),
    "fire":     ("CRITICAL", 1),
    "smoke":    ("URGENT",   2),
    "hazard":   ("URGENT",   2),
    "vehicle":  ("MODERATE", 3),
    "pedestrian":("MODERATE",3),
}


# ─────────────────────────── helper: load detector ─────────────────────────
@st.cache_resource(show_spinner="Loading AI Vision Model…")
def _load_detector():
    try:
        from vision.yolo_detector import YOLOv11Detector
        return YOLOv11Detector(model_name="yolo11n.pt", device="cpu")
    except Exception as e:
        st.warning(f"Vision model init warning: {e} — using heuristic fallback.")
        return None


# ─────────────────────────── helper: draw bboxes ───────────────────────────
def _draw_bboxes(frame_rgb: np.ndarray, detections) -> np.ndarray:
    """Draws coloured bounding boxes and labels onto the frame."""
    pil_img = Image.fromarray(frame_rgb)
    draw    = ImageDraw.Draw(pil_img, "RGBA")

    try:
        font_label = ImageFont.truetype("arial.ttf", 16)
        font_conf  = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font_label = ImageFont.load_default()
        font_conf  = font_label

    for det in detections:
        bbox  = det.bbox
        cat   = det.category
        conf  = det.confidence
        label = det.label
        colour = CATEGORY_COLOURS.get(cat, (250, 204, 21))

        # Bounding box (semi-transparent fill + solid border)
        fill_c  = (*colour, 45)
        bord_c  = (*colour, 220)
        draw.rectangle(
            [bbox.x_min, bbox.y_min, bbox.x_max, bbox.y_max],
            outline=bord_c, width=3, fill=fill_c
        )

        # Label pill background
        lbl_txt = f" {label.upper()} {conf*100:.0f}% "
        bx0, by0 = bbox.x_min, max(0, bbox.y_min - 26)
        draw.rectangle([bx0, by0, bx0 + len(lbl_txt) * 9, by0 + 22],
                       fill=(*colour, 220))
        draw.text((bx0 + 4, by0 + 3), lbl_txt,
                  fill=(0, 0, 0), font=font_label)

    return np.array(pil_img)


# ─────────────────────────── helper: heuristic fallback ────────────────────
def _heuristic_detect(frame: np.ndarray):
    """Simple pixel-based heuristic when YOLO is unavailable (demo mode)."""
    from vision.schemas import DetectedObject, BoundingBox

    h, w = frame.shape[:2]
    objects = []

    # Bright red region → fire
    hsv   = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    mask  = cv2.inRange(hsv, (0, 100, 100), (15, 255, 255))
    mask |= cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
    fire_px = int(np.sum(mask > 0))

    if fire_px > (h * w * 0.03):        # >3% of frame is red/orange
        objects.append(DetectedObject(
            object_id=f"obj-{uuid.uuid4().hex[:6]}",
            class_id=99, label="fire", category="fire",
            confidence=min(0.95, 0.60 + fire_px / (h * w)),
            bbox=BoundingBox(x_min=w*0.10, y_min=h*0.10,
                             x_max=w*0.90, y_max=h*0.90,
                             width=w*0.80, height=h*0.80,
                             area=w*0.80*h*0.80)
        ))

    # Motion / edge density → accident (only works on non-blank frames)
    gray   = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    edges  = cv2.Canny(gray, 50, 150)
    edge_px = int(np.sum(edges > 0))
    if edge_px > (h * w * 0.08) and not objects:
        objects.append(DetectedObject(
            object_id=f"obj-{uuid.uuid4().hex[:6]}",
            class_id=80, label="car crash", category="accident",
            confidence=0.72,
            bbox=BoundingBox(x_min=w*0.25, y_min=h*0.30,
                             x_max=w*0.75, y_max=h*0.80,
                             width=w*0.50, height=h*0.50,
                             area=w*0.50*h*0.50)
        ))

    return objects


# ─────────────────────────── main view ─────────────────────────────────────
def render_webcam_analysis_view():
    """Full Webcam AI analysis view for the Nagpur EOC live demo."""
    render_command_header(
        "LIVE WEBCAM AI ANALYSIS — CAM-0 (LAPTOP)",
        "Real-Time Computer Vision • YOLO Hazard Detection • Auto-Dispatch Pipeline"
    )

    detector = _load_detector()

    # ── Session state init ──────────────────────────────────────────────────
    if "webcam_running"       not in st.session_state:
        st.session_state.webcam_running       = False
    if "last_detections"      not in st.session_state:
        st.session_state.last_detections      = []
    if "incident_dispatched"  not in st.session_state:
        st.session_state.incident_dispatched  = False
    if "dispatch_log"         not in st.session_state:
        st.session_state.dispatch_log         = []
    if "frames_analysed"      not in st.session_state:
        st.session_state.frames_analysed      = 0
    if "hazard_count"         not in st.session_state:
        st.session_state.hazard_count         = 0
    if "confidence_threshold" not in st.session_state:
        st.session_state.confidence_threshold = 0.40

    # ── Control row ─────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1, 1, 1, 2])
    with ctrl1:
        if not st.session_state.webcam_running:
            if st.button("▶️ Start Webcam Analysis", use_container_width=True, type="primary"):
                st.session_state.webcam_running      = True
                st.session_state.incident_dispatched = False
                st.session_state.dispatch_log        = []
                st.session_state.frames_analysed     = 0
                st.session_state.hazard_count        = 0
                st.rerun()
        else:
            if st.button("⏹️ Stop Analysis", use_container_width=True):
                st.session_state.webcam_running = False
                st.rerun()
    with ctrl2:
        if st.button("🔄 Reset Dispatch Log", use_container_width=True):
            st.session_state.incident_dispatched = False
            st.session_state.dispatch_log        = []
            st.session_state.hazard_count        = 0
            st.rerun()
    with ctrl3:
        demo_mode = st.toggle("🤖 Force Demo Detections", value=False,
                               help="Always inject bounding boxes even on a clean frame (for demo)")
    with ctrl4:
        conf_t = st.slider("Confidence Threshold", 0.20, 0.90,
                           st.session_state.confidence_threshold, 0.05,
                           help="Minimum AI confidence to flag an object")
        st.session_state.confidence_threshold = conf_t

    st.markdown("---")

    # ── Main layout ─────────────────────────────────────────────────────────
    cam_col, panel_col = st.columns([1.6, 1])

    frame_placeholder    = cam_col.empty()
    status_placeholder   = cam_col.empty()
    metrics_placeholder  = st.empty()

    with panel_col:
        st.subheader("🚨 EOC Incident Command Panel")
        dispatch_placeholder = st.empty()
        log_placeholder      = st.empty()

    # ── Webcam capture + analysis loop ──────────────────────────────────────
    if st.session_state.webcam_running:
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            cam_col.error("❌ Webcam not accessible (index 0). Check camera permissions or try a different index.")
            st.session_state.webcam_running = False
            cap.release()
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Capture exactly 1 frame per Streamlit run (Streamlit reruns on st.rerun())
            ret, frame = cap.read()
            cap.release()

            if not ret:
                status_placeholder.warning("⚠️ Failed to read webcam frame. Retrying…")
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                st.session_state.frames_analysed += 1

                t0 = time.perf_counter()

                # ── Run detection ──────────────────────────────────────────
                if detector is not None:
                    detections = detector.predict(frame_rgb, conf_t)
                else:
                    detections = _heuristic_detect(frame_rgb)

                # Inject demo bboxes on top of real ones when demo mode is on
                if demo_mode:
                    from vision.schemas import DetectedObject, BoundingBox
                    h, w = frame_rgb.shape[:2]
                    demo_objs = [
                        DetectedObject(
                            object_id=f"demo-{uuid.uuid4().hex[:4]}",
                            class_id=80, label="car crash",
                            category="accident", confidence=0.89,
                            bbox=BoundingBox(x_min=w*0.15, y_min=h*0.25,
                                             x_max=w*0.60, y_max=h*0.80,
                                             width=w*0.45, height=h*0.55,
                                             area=w*0.45*h*0.55)
                        ),
                        DetectedObject(
                            object_id=f"demo-{uuid.uuid4().hex[:4]}",
                            class_id=0, label="person",
                            category="pedestrian", confidence=0.82,
                            bbox=BoundingBox(x_min=w*0.65, y_min=h*0.30,
                                             x_max=w*0.80, y_max=h*0.85,
                                             width=w*0.15, height=h*0.55,
                                             area=w*0.15*h*0.55)
                        ),
                    ]
                    # Merge: avoid duplicates by category
                    existing_cats = {d.category for d in detections}
                    for d in demo_objs:
                        if d.category not in existing_cats:
                            detections.append(d)

                latency_ms = (time.perf_counter() - t0) * 1000

                # ── Draw boxes ─────────────────────────────────────────────
                annotated = _draw_bboxes(frame_rgb, detections)
                frame_placeholder.image(
                    annotated,
                    caption=f"📹 Webcam (CAM-0) — {datetime.datetime.now().strftime('%H:%M:%S')} | "
                            f"AI Latency: {latency_ms:.0f}ms | Objects: {len(detections)}",
                    use_container_width=True
                )

                st.session_state.last_detections = detections

                # Track hazards
                critical_cats = {"accident", "fire", "smoke"}
                hazardous = [d for d in detections if d.category in critical_cats]
                if hazardous:
                    st.session_state.hazard_count += 1

                # ── Status bar ─────────────────────────────────────────────
                if hazardous:
                    status_placeholder.error(
                        f"🚨 **HAZARD DETECTED**: "
                        + " | ".join(f"{d.label.upper()} ({d.confidence*100:.0f}%)"
                                     for d in hazardous)
                    )
                else:
                    status_placeholder.success("✅ Scene CLEAR — No Emergency Hazards Detected")

                # ── Auto-Dispatch Panel ────────────────────────────────────
                with dispatch_placeholder.container():
                    if hazardous:
                        top = max(hazardous, key=lambda d: d.confidence)
                        priority, level = PRIORITY_MAP.get(top.category, ("MODERATE", 3))

                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #7f1d1d, #450a0a);
                            border: 2px solid #ef4444;
                            border-radius: 12px;
                            padding: 16px;
                            animation: pulse 1s infinite;">
                            <h3 style="color:#fca5a5; margin:0">🚨 INCIDENT DETECTED</h3>
                            <p style="color:#fef2f2; margin:4px 0">
                                <b>Hazard:</b> {top.label.upper()}<br>
                                <b>Confidence:</b> {top.confidence*100:.1f}%<br>
                                <b>Priority:</b> {priority} (Level {level})<br>
                                <b>Suggested Hospital:</b> GMCH Nagpur Level I<br>
                                <b>Nearest Unit:</b> NMC-AMB-101 (ALS)
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            if st.button("🚑 AUTO DISPATCH", type="primary",
                                         use_container_width=True,
                                         key=f"dispatch_{st.session_state.frames_analysed}"):
                                inc_id = f"INC-{uuid.uuid4().hex[:4].upper()}"
                                log_entry = {
                                    "time":      datetime.datetime.now().strftime("%H:%M:%S"),
                                    "incident":  inc_id,
                                    "hazard":    top.label.upper(),
                                    "priority":  priority,
                                    "unit":      "NMC-AMB-101",
                                    "hospital":  "GMCH Nagpur",
                                    "eta":       "4.2 min",
                                    "confidence": f"{top.confidence*100:.1f}%"
                                }
                                st.session_state.dispatch_log.insert(0, log_entry)
                                st.session_state.incident_dispatched = True
                                st.toast(f"🚨 Dispatched to {inc_id}!", icon="🚑")
                        with col_d2:
                            if st.button("🔕 Acknowledge", use_container_width=True,
                                         key=f"ack_{st.session_state.frames_analysed}"):
                                st.session_state.hazard_count = 0
                    else:
                        st.markdown("""
                        <div style="
                            background: linear-gradient(135deg, #064e3b, #022c22);
                            border: 2px solid #10b981;
                            border-radius: 12px; padding: 16px;">
                            <h3 style="color:#6ee7b7; margin:0">✅ ALL CLEAR</h3>
                            <p style="color:#d1fae5; margin:4px 0">
                                No emergency hazards detected.<br>Continuous monitoring active.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                # ── Dispatch log ───────────────────────────────────────────
                if st.session_state.dispatch_log:
                    with log_placeholder.container():
                        st.markdown("#### 📋 Dispatch Log")
                        for entry in st.session_state.dispatch_log[:5]:
                            st.markdown(
                                f"🕐 `{entry['time']}` **{entry['incident']}** — "
                                f"{entry['hazard']} ({entry['confidence']}) → "
                                f"{entry['unit']} @ {entry['hospital']} ETA {entry['eta']}"
                            )

        # ── Live metrics row ───────────────────────────────────────────────
        with metrics_placeholder.container():
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                render_metric_card("Frames Analysed",
                                   str(st.session_state.frames_analysed),
                                   "Since session start", "cyan")
            with m2:
                render_metric_card("Objects Detected",
                                   str(len(st.session_state.last_detections)),
                                   "Current frame", "emerald")
            with m3:
                render_metric_card("Hazard Events",
                                   str(st.session_state.hazard_count),
                                   "Consecutive alerts", "red")
            with m4:
                render_metric_card("Dispatches Sent",
                                   str(len(st.session_state.dispatch_log)),
                                   "This session", "amber")

        # ── Auto-rerun to capture next frame ──────────────────────────────
        time.sleep(0.4)          # ~2.5 fps to stay within Streamlit limits
        st.rerun()

    else:
        # ── Idle state ─────────────────────────────────────────────────────
        cam_col.markdown("""
        <div style="
            background: linear-gradient(135deg, #0f172a, #1e293b);
            border: 2px dashed #334155;
            border-radius: 16px;
            height: 380px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 2rem;">
            <div>
                <div style="font-size: 4rem;">📷</div>
                <h2 style="color: #64748b; margin: 12px 0 8px">Webcam Standby</h2>
                <p style="color: #475569; font-size: 1rem;">
                    Press <b style="color:#06b6d4">▶️ Start Webcam Analysis</b> to activate<br>
                    real-time YOLO hazard detection from your laptop camera.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with panel_col:
            st.info("""
            **How to run the demo:**

            1. Click **▶️ Start Webcam Analysis**
            2. Point your webcam at something — or hold up a phone screen showing an accident image
            3. Enable **🤖 Force Demo Detections** to always show bounding boxes
            4. When a hazard is flagged, press **🚑 AUTO DISPATCH**
            5. Watch the EOC dispatch log populate in real-time
            """)

        # Show last captured frame if any
        if st.session_state.last_detections:
            cam_col.markdown("#### Last Analysed Frame Detections")
            for d in st.session_state.last_detections:
                cam_col.markdown(
                    f"- `{d.label.upper()}` — confidence `{d.confidence*100:.1f}%` "
                    f"[{d.category.upper()}]"
                )

    # ── Detection legend ────────────────────────────────────────────────────
    with st.expander("🎨 Detection Category Colour Legend"):
        legend_cols = st.columns(len(CATEGORY_COLOURS))
        for col, (cat, rgb) in zip(legend_cols, CATEGORY_COLOURS.items()):
            col.markdown(
                f'<div style="background:rgb{rgb}; border-radius:6px; '
                f'padding:6px 10px; color:#000; font-weight:bold; '
                f'text-align:center">{cat.upper()}</div>',
                unsafe_allow_html=True
            )
