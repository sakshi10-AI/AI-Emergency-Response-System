"""
Vision Detection Service

Exposes high-level async and sync APIs for computer vision detection, image uploads,
video processing, and live camera streams. Unifies classical YOLO object detection
with Multimodal Vision-Language (VLM) scene reasoning and temporal video persistence.
"""

from typing import Any, Optional, Tuple, Dict
import io
import base64
import numpy as np
from PIL import Image

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from vision.pipeline import InferencePipeline
from vision.schemas import VisionInferenceResult, VideoInferenceResult
from vision.config import vision_config, VisionConfig
from vision.model_loader import model_loader
from vision.vlm_analyzer import vlm_analyzer, VLMSceneAnalysisResult
from vision.temporal_analyzer import temporal_video_analyzer, VideoTemporalAnalysisResult
from vision.quality_gate import quality_gate
from utils.logger import app_logger


class VisionDetectionService:
    """Service bridge for computer vision and multimodal VLM inference requests."""

    def __init__(self, config: Optional[VisionConfig] = None):
        self.config = config or vision_config
        self.pipeline = InferencePipeline(config=self.config)

    def set_detector(self, model_type: str = "yolo11", model_name: str = "yolo11n.pt", device: str = "cpu"):
        """Swaps active model detector."""
        detector = model_loader.get_detector(model_type=model_type, model_name=model_name, device=device)
        self.pipeline = InferencePipeline(detector=detector, config=self.config)
        app_logger.info(f"[VisionDetectionService] Detector swapped to '{model_name}' on '{device}'.")

    # =========================================================================
    # VLM Multimodal & Enhanced Video Analysis
    # =========================================================================

    async def analyze_image_vlm(
        self,
        image_source: Any,
        prompt_hint: Optional[str] = None,
        draw_annotations: bool = True
    ) -> Tuple[VLMSceneAnalysisResult, Optional[str]]:
        """
        Runs Multimodal VLM scene analysis on an image.
        Returns (VLMSceneAnalysisResult, annotated_image_base64).
        """
        analysis = await vlm_analyzer.analyze_image_async(image_source, prompt_hint=prompt_hint)
        annotated_b64 = None

        if draw_annotations:
            annotated_b64 = self._draw_vlm_annotations(image_source, analysis)

        return analysis, annotated_b64

    async def analyze_video_temporal(
        self,
        video_input: Any,
        sample_interval_sec: float = 1.0
    ) -> VideoTemporalAnalysisResult:
        """
        Runs multi-frame temporal consistency and hazard persistence analysis on video.
        """
        return await temporal_video_analyzer.analyze_video_async(
            video_input=video_input,
            sample_interval_sec=sample_interval_sec
        )

    def _draw_vlm_annotations(self, image_source: Any, result: VLMSceneAnalysisResult) -> Optional[str]:
        """Draws dynamically detected bounding boxes and clinical triage overlay."""
        try:
            # Load frame
            if isinstance(image_source, bytes):
                pil_img = Image.open(io.BytesIO(image_source)).convert("RGB")
                frame = np.array(pil_img)[:, :, ::-1].copy()
            elif isinstance(image_source, Image.Image):
                frame = np.array(image_source.convert("RGB"))[:, :, ::-1].copy()
            elif isinstance(image_source, np.ndarray):
                frame = image_source.copy()
            else:
                return None

            h, w = frame.shape[:2]

            # Category BGR Colors
            colors = {
                "accident": (0, 0, 255),       # Red
                "fire": (0, 100, 255),         # Orange
                "smoke": (140, 140, 140),      # Gray
                "vehicle": (255, 180, 0),      # Cyan
                "pedestrian": (0, 255, 0),     # Green
                "hazard": (255, 0, 255),       # Magenta
            }

            if OPENCV_AVAILABLE:
                for b in result.bounding_boxes:
                    ymin, xmin, ymax, xmax = [
                        int(v * (h if i % 2 == 0 else w) / 1000.0)
                        for i, v in enumerate(b.box_2d)
                    ]
                    color = colors.get(b.category, (0, 0, 255))
                    cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 3)
                    
                    label_text = f"{b.label} ({int(b.confidence * 100)}%)"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                    cv2.rectangle(frame, (xmin, max(ymin - 24, 0)), (xmin + tw + 6, max(ymin, 24)), color, -1)
                    cv2.putText(frame, label_text, (xmin + 3, max(ymin - 6, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

                # Severity header badge
                badge_text = f"TRIAGE SCORE: {result.severity_score}/100 [{result.severity_level}] | PREALERT: {result.target_hospital_phone}"
                badge_bg = (0, 0, 200) if result.severity_score >= 75 else (0, 140, 255)
                cv2.rectangle(frame, (0, 0), (w, 36), badge_bg, -1)
                cv2.putText(frame, badge_text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                _, buf = cv2.imencode(".jpg", frame)
                return base64.b64encode(buf.tobytes()).decode("utf-8")
            else:
                # PIL fallback drawing
                from PIL import ImageDraw
                pil_draw = Image.fromarray(frame[:, :, ::-1])
                draw = ImageDraw.Draw(pil_draw)
                for b in result.bounding_boxes:
                    ymin, xmin, ymax, xmax = [
                        int(v * (h if i % 2 == 0 else w) / 1000.0)
                        for i, v in enumerate(b.box_2d)
                    ]
                    draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=3)
                buf = io.BytesIO()
                pil_draw.save(buf, format="JPEG")
                return base64.b64encode(buf.getvalue()).decode("utf-8")

        except Exception as e:
            app_logger.error(f"[VisionDetectionService] Error drawing annotations: {e}")
            return None

    # =========================================================================
    # Backwards-Compatible Legacy Pipeline APIs
    # =========================================================================

    async def detect_image_async(self, image_source: Any, draw_annotations: bool = True) -> VisionInferenceResult:
        """Async interface for processing image upload via YOLO pipeline."""
        return self.pipeline.process_image(image_source=image_source, draw_annotations=draw_annotations)

    def detect_image_sync(self, image_source: Any, draw_annotations: bool = True) -> VisionInferenceResult:
        """Sync interface for processing image upload via YOLO pipeline."""
        return self.pipeline.process_image(image_source=image_source, draw_annotations=draw_annotations)

    async def detect_video_async(self, video_path: str, sample_rate: Optional[int] = None) -> VideoInferenceResult:
        """Async interface for processing video upload via YOLO pipeline."""
        return self.pipeline.process_video(video_path=video_path, sample_rate=sample_rate)

    def detect_video_sync(self, video_path: str, sample_rate: Optional[int] = None) -> VideoInferenceResult:
        """Sync interface for processing video upload via YOLO pipeline."""
        return self.pipeline.process_video(video_path=video_path, sample_rate=sample_rate)


# Global Service Instance
vision_detection_service = VisionDetectionService()
