"""
Vision Detection Service

Exposes high-level async and sync APIs for computer vision detection, image uploads,
video processing, and live camera streams.
"""

from typing import Any, Optional
from vision.pipeline import InferencePipeline
from vision.schemas import VisionInferenceResult, VideoInferenceResult
from vision.config import vision_config, VisionConfig
from vision.model_loader import model_loader
from utils.logger import app_logger


class VisionDetectionService:
    """Service bridge for computer vision inference requests."""

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or vision_config
        self.pipeline = InferencePipeline(config=self.config)

    def set_detector(self, model_type: str = "yolo11", model_name: str = "yolo11n.pt", device: str = "cpu"):
        """Swaps active model detector."""
        detector = model_loader.get_detector(model_type=model_type, model_name=model_name, device=device)
        self.pipeline = InferencePipeline(detector=detector, config=self.config)
        app_logger.info(f"[VisionDetectionService] Detector swapped to '{model_name}' on '{device}'.")

    async def detect_image_async(self, image_source: Any, draw_annotations: bool = True) -> VisionInferenceResult:
        """Async interface for processing image upload."""
        return self.pipeline.process_image(image_source=image_source, draw_annotations=draw_annotations)

    def detect_image_sync(self, image_source: Any, draw_annotations: bool = True) -> VisionInferenceResult:
        """Sync interface for processing image upload."""
        return self.pipeline.process_image(image_source=image_source, draw_annotations=draw_annotations)

    async def detect_video_async(self, video_path: str, sample_rate: Optional[int] = None) -> VideoInferenceResult:
        """Async interface for processing video upload."""
        return self.pipeline.process_video(video_path=video_path, sample_rate=sample_rate)

    def detect_video_sync(self, video_path: str, sample_rate: Optional[int] = None) -> VideoInferenceResult:
        """Sync interface for processing video upload."""
        return self.pipeline.process_video(video_path=video_path, sample_rate=sample_rate)


# Global Service Instance
vision_detection_service = VisionDetectionService()
