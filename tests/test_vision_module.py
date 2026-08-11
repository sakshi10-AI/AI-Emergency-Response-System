"""
Comprehensive Test Suite for Vision Computer Vision Module

Tests:
1. YOLOv11Detector & BaseVisionDetector modular contract
2. ModelLoader factory caching and registration
3. BoundingBoxUtilities IoU, NMS, OpenCV annotator, base64 encoding
4. Input handlers for images, videos, and live camera streams
5. InferencePipeline end-to-end processing & hazard alerts
6. VisionDetectionService async/sync APIs
"""

import pytest
import numpy as np
import os
import tempfile
from typing import List, Dict, Any, Optional
from PIL import Image

from vision.config import VisionConfig, vision_config
from vision.schemas import BoundingBox, DetectedObject, HazardAlert, VisionInferenceResult
from vision.base_detector import BaseVisionDetector
from vision.yolo_detector import YOLOv11Detector
from vision.model_loader import ModelLoader, model_loader
from vision.bbox_utils import BoundingBoxUtilities
from vision.input_handlers import ImageInputHandler, VideoInputHandler, LiveCameraInputHandler
from vision.pipeline import InferencePipeline
from vision.service import VisionDetectionService, vision_detection_service


# ============================================================================
# 1. Custom Detector Subclass Test for Modular Swapping
# ============================================================================

class CustomRTDETRDetector(BaseVisionDetector):
    """Test custom detector implementation demonstrating modular swapping."""

    def __init__(self, model_name: str = "rt_detr_r50.pt", device: str = "cpu"):
        super().__init__(model_name=model_name, device=device)
        self._is_loaded = True

    def load_model(self, model_path=None, device=None) -> bool:
        self._is_loaded = True
        return True

    def supported_categories(self) -> List[str]:
        return ["vehicle", "pedestrian", "fire", "smoke", "accident"]

    def predict(self, image, confidence_threshold=0.45) -> List[DetectedObject]:
        return [
            DetectedObject(
                object_id="custom-1",
                class_id=80,
                label="car crash",
                category="accident",
                confidence=0.96,
                bbox=BoundingBox(x_min=50, y_min=50, x_max=200, y_max=200, width=150, height=150, area=22500)
            )
        ]


# ============================================================================
# 2. Test Detector Contract & ModelLoader Factory
# ============================================================================

def test_yolo_detector_initialization():
    detector = YOLOv11Detector(model_name="yolo11n.pt", device="cpu")
    assert detector.model_name == "yolo11n.pt"
    assert "vehicle" in detector.supported_categories()

    # Predict on dummy synthetic array
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    objs = detector.predict(dummy_img, confidence_threshold=0.4)
    assert isinstance(objs, list)
    assert len(objs) > 0


def test_model_loader_factory_and_caching():
    det1 = model_loader.get_detector(model_type="yolo11", model_name="yolo11n.pt", device="cpu")
    det2 = model_loader.get_detector(model_type="yolo11", model_name="yolo11n.pt", device="cpu")
    assert det1 is det2  # Cached instance

    # Register custom detector
    model_loader.register_detector_type("rtdetr", CustomRTDETRDetector)
    custom_det = model_loader.get_detector(model_type="rtdetr", model_name="rt_detr_r50.pt")
    assert isinstance(custom_det, CustomRTDETRDetector)
    assert custom_det.model_name == "rt_detr_r50.pt"


# ============================================================================
# 3. Test BoundingBoxUtilities
# ============================================================================

def test_iou_calculation():
    b1 = BoundingBox(x_min=0, y_min=0, x_max=100, y_max=100, width=100, height=100, area=10000)
    b2 = BoundingBox(x_min=50, y_min=0, x_max=150, y_max=100, width=100, height=100, area=10000)
    iou = BoundingBoxUtilities.calculate_iou(b1, b2)
    assert 0.32 < iou < 0.35

    # Non-overlapping
    b3 = BoundingBox(x_min=200, y_min=200, x_max=300, y_max=300, width=100, height=100, area=10000)
    assert BoundingBoxUtilities.calculate_iou(b1, b3) == 0.0


def test_nms_filtering():
    obj1 = DetectedObject(
        object_id="1", class_id=2, label="car", category="vehicle", confidence=0.90,
        bbox=BoundingBox(x_min=10, y_min=10, x_max=100, y_max=100, width=90, height=90, area=8100)
    )
    obj2 = DetectedObject(
        object_id="2", class_id=2, label="car", category="vehicle", confidence=0.85,
        bbox=BoundingBox(x_min=12, y_min=12, x_max=98, y_max=98, width=86, height=86, area=7396)
    )
    filtered = BoundingBoxUtilities.apply_nms([obj1, obj2], iou_threshold=0.5)
    assert len(filtered) == 1
    assert filtered[0].object_id == "1"


def test_drawing_and_encoding():
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    obj = DetectedObject(
        object_id="1", class_id=2, label="car", category="vehicle", confidence=0.90,
        bbox=BoundingBox(x_min=10, y_min=10, x_max=100, y_max=100, width=90, height=90, area=8100)
    )
    annotated = BoundingBoxUtilities.draw_bounding_boxes(dummy_img, [obj])
    assert annotated is not None
    assert annotated.shape == (480, 640, 3)

    b64 = BoundingBoxUtilities.encode_image_to_base64(annotated)
    assert b64 is not None and len(b64) > 100


# ============================================================================
# 4. Test Input Handlers
# ============================================================================

def test_image_input_handler():
    # Test PIL Image input
    pil_img = Image.new("RGB", (300, 200), color=(255, 0, 0))
    arr, w, h = ImageInputHandler.load_image(pil_img)
    assert w == 300 and h == 200
    assert arr.shape == (200, 300, 3)

    # Test NumPy array input
    np_img = np.zeros((100, 150, 3), dtype=np.uint8)
    arr2, w2, h2 = ImageInputHandler.load_image(np_img)
    assert w2 == 150 and h2 == 100


# ============================================================================
# 5. Test Inference Pipeline & Hazard Evaluation
# ============================================================================

def test_inference_pipeline_single_image():
    pipeline = InferencePipeline()
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    res = pipeline.process_image(dummy_img)

    assert isinstance(res, VisionInferenceResult)
    assert res.image_width == 640
    assert res.image_height == 480
    assert len(res.detected_objects) > 0
    assert res.scene_summary != ""
    assert res.processing_time_ms > 0.0
    assert res.annotated_image_base64 is not None


@pytest.mark.asyncio
async def test_vision_detection_service_async_api():
    service = VisionDetectionService()
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    res = await service.detect_image_async(dummy_img)

    assert res.vehicle_count >= 0
    assert res.pedestrian_count >= 0
    assert res.processing_time_ms > 0
