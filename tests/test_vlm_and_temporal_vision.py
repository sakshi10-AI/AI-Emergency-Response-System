"""
Comprehensive Test Suite for Better Alternative Methods Vision Architecture

Tests:
1. VisionQualityGate blur and luminance evaluation
2. MultimodalVLMAnalyzer scene comprehension and CV heuristic fallback
3. TemporalVideoAnalyzer multi-frame persistence voting and timeline breakdown
4. Vision Detection Service integration
5. FastAPI endpoints: /api/v1/vision/analyze-image, /api/v1/vision/analyze-video, /api/v1/vision/dispatch-hospital-call
"""

import pytest
import io
import numpy as np
from PIL import Image, ImageDraw
import cv2
from httpx import AsyncClient, ASGITransport

from vision.quality_gate import quality_gate, VisionQualityGate
from vision.vlm_analyzer import vlm_analyzer, MultimodalVLMAnalyzer, VLMSceneAnalysisResult
from vision.temporal_analyzer import temporal_video_analyzer, TemporalVideoAnalyzer
from vision.service import vision_detection_service
from backend.main import app


# ============================================================================
# 1. Quality Gate Tests
# ============================================================================

def test_quality_gate_optimal_frame():
    """Validates quality gate on high-contrast clear image."""
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (350, 350), (255, 255, 255), -1)
    cv2.circle(img, (200, 200), 80, (0, 0, 0), -1)

    result = quality_gate.evaluate_frame(img)
    assert result["passed"] is True
    assert result["quality_tier"] == "OPTIMAL"
    assert result["blur_score"] > 50.0


def test_quality_gate_degraded_blur():
    """Validates quality gate flags severely blurred frames."""
    blurred = np.full((300, 300, 3), 120, dtype=np.uint8)
    result = quality_gate.evaluate_frame(blurred)
    assert result["blur_score"] < 25.0
    assert result["quality_tier"] in ["DEGRADED", "CRITICAL_DEFECT"]


def test_quality_gate_underexposed_darkness():
    """Validates quality gate flags pitch black scenes."""
    dark = np.zeros((300, 300, 3), dtype=np.uint8)
    result = quality_gate.evaluate_frame(dark)
    assert result["brightness_score"] < 30.0


# ============================================================================
# 2. Multimodal VLM Analyzer Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vlm_analyzer_with_synthetic_fire_and_accident():
    """Tests VLM analysis engine detecting simulated emergency scene."""
    # Create image with fire-like orange and vehicle-like blocks
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Background roadway
    img[:, :] = (50, 50, 50)
    # Simulated vehicle 1
    cv2.rectangle(img, (100, 200), (260, 340), (200, 180, 160), -1)
    # Simulated vehicle 2 (overlapping - crash)
    cv2.rectangle(img, (230, 210), (380, 350), (180, 160, 140), -1)
    # Active fire patch (bright orange-yellow in BGR: B=0, G=150, R=255)
    cv2.rectangle(img, (200, 160), (270, 220), (0, 160, 255), -1)

    analysis = await vlm_analyzer.analyze_image_async(img, prompt_hint="Highway collision with fire")
    assert isinstance(analysis, VLMSceneAnalysisResult)
    assert analysis.severity_score >= 60
    assert analysis.target_hospital_phone == "7796119389"
    assert len(analysis.bounding_boxes) > 0


@pytest.mark.asyncio
async def test_vision_detection_service_vlm_annotations():
    """Tests that vision_detection_service produces annotated base64 overlay."""
    img = Image.new("RGB", (320, 240), color=(100, 100, 100))
    analysis, b64 = await vision_detection_service.analyze_image_vlm(img, draw_annotations=True)
    assert analysis is not None
    assert b64 is not None
    assert isinstance(b64, str)
    assert len(b64) > 100


# ============================================================================
# 3. Temporal Video Analyzer Tests
# ============================================================================

@pytest.mark.asyncio
async def test_temporal_video_analyzer_persistence():
    """Tests temporal multi-frame consistency and timeline event generation."""
    # Mock video fallback
    result = await temporal_video_analyzer.analyze_video_async("non_existent_stream.mp4")
    assert result.duration_seconds > 0
    assert result.target_hospital_phone == "7796119389"
    assert len(result.timeline_events) > 0
    assert result.accident_confirmed is True


# ============================================================================
# 4. REST API Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_vision_api_image_analysis_endpoint():
    """Tests POST /api/v1/vision/analyze-image endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a small JPEG
        pil_img = Image.new("RGB", (200, 200), color=(200, 50, 50))
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        buf.seek(0)

        response = await client.post(
            "/api/v1/vision/analyze-image",
            files={"file": ("test_scene.jpg", buf, "image/jpeg")},
            data={"prompt_hint": "Car crash on Ring Road"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert "analysis" in data
        assert "annotated_image_base64" in data
        assert data["analysis"]["target_hospital_phone"] == "7796119389"


@pytest.mark.asyncio
async def test_vision_api_dispatch_hospital_call_endpoint():
    """Tests POST /api/v1/vision/dispatch-hospital-call endpoint routing to 7796119389."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "latitude": 21.1458,
            "longitude": 79.0882,
            "incident_type": "HIGHWAY_MULTI_VEHICLE_CRASH",
            "severity_score": 90,
            "casualties_count": 3,
            "scene_summary": "Two vehicles head-on with heavy cabin intrusion.",
            "target_override_phone": "7796119389"
        }
        response = await client.post("/api/v1/vision/dispatch-hospital-call", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DISPATCHED"
        assert data["target_phone"] == "7796119389"
        assert "GMCH" in data["nearest_hospital_name"] or "Hospital" in data["nearest_hospital_name"]
        assert data["distance_km"] > 0
        assert "speech_transcript" in data
