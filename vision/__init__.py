"""
Vision Computer Vision Core Package

Exposes YOLOv11 & custom detectors, model loaders, bounding box utilities,
input stream handlers, inference pipeline, and high-level vision detection services.
"""

from vision.config import VisionConfig, vision_config
from vision.schemas import (
    BoundingBox, DetectedObject, HazardAlert,
    VisionInferenceResult, VideoInferenceResult
)
from vision.base_detector import BaseVisionDetector
from vision.yolo_detector import YOLOv11Detector
from vision.model_loader import ModelLoader, model_loader
from vision.bbox_utils import BoundingBoxUtilities
from vision.input_handlers import ImageInputHandler, VideoInputHandler, LiveCameraInputHandler
from vision.pipeline import InferencePipeline
from vision.service import VisionDetectionService, vision_detection_service

__all__ = [
    "VisionConfig",
    "vision_config",
    "BoundingBox",
    "DetectedObject",
    "HazardAlert",
    "VisionInferenceResult",
    "VideoInferenceResult",
    "BaseVisionDetector",
    "YOLOv11Detector",
    "ModelLoader",
    "model_loader",
    "BoundingBoxUtilities",
    "ImageInputHandler",
    "VideoInputHandler",
    "LiveCameraInputHandler",
    "InferencePipeline",
    "VisionDetectionService",
    "vision_detection_service"
]
