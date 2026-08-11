"""
Vision Inference Pipeline

Coordinates input handling, detector inference, NMS post-processing,
emergency hazard evaluation, visual annotation, and Pydantic JSON formatting.
"""

import time
import uuid
from typing import Any, List, Optional, Union
import numpy as np

from vision.config import vision_config, VisionConfig
from vision.model_loader import model_loader
from vision.base_detector import BaseVisionDetector
from vision.bbox_utils import BoundingBoxUtilities
from vision.input_handlers import ImageInputHandler, VideoInputHandler, LiveCameraInputHandler
from vision.schemas import (
    VisionInferenceResult, VideoInferenceResult, DetectedObject, HazardAlert
)
from utils.logger import app_logger


class InferencePipeline:
    """
    Modular Computer Vision Inference Pipeline.
    Supports single images, video files, and live RTSP/webcam camera streams.
    """

    def __init__(self, detector: Optional[BaseVisionDetector] = None, config: Optional[VisionConfig] = None):
        self.config = config or vision_config
        self.detector = detector or model_loader.get_detector(
            model_name=self.config.model_name,
            device=self.config.device
        )

    def process_image(
        self,
        image_source: Any,
        draw_annotations: bool = True,
        confidence_threshold: Optional[float] = None
    ) -> VisionInferenceResult:
        """
        Executes end-to-end vision pipeline on a single image.
        """
        start_time = time.time()
        conf_thresh = confidence_threshold or self.config.confidence_threshold

        # 1. Load image frame
        frame, w, h = ImageInputHandler.load_image(image_source)

        # 2. Run detector inference
        raw_detections = self.detector.predict(frame, confidence_threshold=conf_thresh)

        # 3. Apply NMS filtering
        filtered_objects = BoundingBoxUtilities.apply_nms(
            raw_detections,
            iou_threshold=self.config.nms_iou_threshold
        )

        # 4. Count object categories & evaluate hazard alerts
        vehicles = [obj for obj in filtered_objects if obj.category == "vehicle"]
        pedestrians = [obj for obj in filtered_objects if obj.category == "pedestrian"]
        accidents = [obj for obj in filtered_objects if obj.category == "accident"]
        fires = [obj for obj in filtered_objects if obj.category == "fire"]
        smokes = [obj for obj in filtered_objects if obj.category == "smoke"]

        fire_detected = len(fires) > 0
        smoke_detected = len(smokes) > 0
        accident_detected = len(accidents) > 0

        # Assess hazard alerts
        hazard_alerts = self._evaluate_hazards(
            objects=filtered_objects,
            fire=fire_detected,
            smoke=smoke_detected,
            accident=accident_detected,
            vehicle_count=len(vehicles),
            pedestrian_count=len(pedestrians)
        )

        # 5. Draw bounding box annotations if requested
        annotated_b64 = None
        if draw_annotations and frame is not None:
            annotated_frame = BoundingBoxUtilities.draw_bounding_boxes(
                frame,
                filtered_objects,
                hazard_alerts=hazard_alerts
            )
            annotated_b64 = BoundingBoxUtilities.encode_image_to_base64(annotated_frame)

        # 6. Synthesize scene summary
        summary = self._generate_scene_summary(
            len(vehicles), len(pedestrians), fire_detected, smoke_detected, accident_detected, hazard_alerts
        )

        latency_ms = max(0.01, round((time.time() - start_time) * 1000.0, 2))

        return VisionInferenceResult(
            frame_id=f"frame-{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            image_width=w,
            image_height=h,
            detected_objects=filtered_objects,
            vehicle_count=len(vehicles),
            pedestrian_count=len(pedestrians),
            victim_count=len(pedestrians) if accident_detected else 0,
            fire_detected=fire_detected,
            smoke_detected=smoke_detected,
            accident_detected=accident_detected,
            hazard_alerts=hazard_alerts,
            scene_summary=summary,
            processing_time_ms=latency_ms,
            model_used=self.detector.model_name,
            annotated_image_base64=annotated_b64
        )

    def process_video(
        self,
        video_path: str,
        sample_rate: Optional[int] = None
    ) -> VideoInferenceResult:
        """
        Executes end-to-end vision pipeline on a video file upload.
        """
        start_time = time.time()
        rate = sample_rate or self.config.frame_sample_rate
        sample_results: List[VisionInferenceResult] = []

        max_vehicles = 0
        max_pedestrians = 0
        any_fire = False
        any_smoke = False
        any_accident = False
        critical_alerts: List[HazardAlert] = []

        for frame_idx, frame_bgr, timestamp in VideoInputHandler.extract_frames(video_path, frame_sample_rate=rate):
            res = self.process_image(frame_bgr, draw_annotations=False)
            sample_results.append(res)

            max_vehicles = max(max_vehicles, res.vehicle_count)
            max_pedestrians = max(max_pedestrians, res.pedestrian_count)
            if res.fire_detected: any_fire = True
            if res.smoke_detected: any_smoke = True
            if res.accident_detected: any_accident = True
            critical_alerts.extend(res.hazard_alerts)

        elapsed = time.time() - start_time
        summary = (
            f"Processed {len(sample_results)} sample frames. "
            f"Max vehicles: {max_vehicles}, Max pedestrians: {max_pedestrians}. "
            f"Fire: {'YES' if any_fire else 'NO'}, Accident: {'YES' if any_accident else 'NO'}."
        )

        return VideoInferenceResult(
            source_name=video_path,
            total_frames_processed=len(sample_results),
            duration_seconds=round(elapsed, 2),
            fps=round(len(sample_results) / max(elapsed, 0.01), 1),
            max_vehicle_count=max_vehicles,
            max_pedestrian_count=max_pedestrians,
            fire_detected_any_frame=any_fire,
            smoke_detected_any_frame=any_smoke,
            accident_detected_any_frame=any_accident,
            critical_alerts=critical_alerts[:5],
            overall_scene_summary=summary,
            frame_samples=sample_results[:10]  # Return up to 10 sample frame details
        )

    def _evaluate_hazards(
        self,
        objects: List[DetectedObject],
        fire: bool,
        smoke: bool,
        accident: bool,
        vehicle_count: int,
        pedestrian_count: int
    ) -> List[HazardAlert]:
        """Evaluates detected objects and raises structured HazardAlerts."""
        alerts = []

        if accident:
            alerts.append(HazardAlert(
                hazard_id=f"haz-{uuid.uuid4().hex[:6]}",
                hazard_type="ACCIDENT",
                risk_tier="CRITICAL",
                title="Vehicle Collision Detected",
                description="Visual evidence indicates an active vehicle accident/crash scene.",
                confidence=0.92
            ))

        if fire:
            alerts.append(HazardAlert(
                hazard_id=f"haz-{uuid.uuid4().hex[:6]}",
                hazard_type="FIRE",
                risk_tier="CRITICAL",
                title="Active Fire Hazard Detected",
                description="Active flame / fire hazard identified in visual frame.",
                confidence=0.95
            ))

        if smoke:
            alerts.append(HazardAlert(
                hazard_id=f"haz-{uuid.uuid4().hex[:6]}",
                hazard_type="SMOKE",
                risk_tier="HIGH",
                title="Smoke Plume Detected",
                description="Heavy smoke plume detected in scene perimeter.",
                confidence=0.88
            ))

        if accident and pedestrian_count > 0:
            alerts.append(HazardAlert(
                hazard_id=f"haz-{uuid.uuid4().hex[:6]}",
                hazard_type="PEDESTRIAN_IN_DANGER",
                risk_tier="CRITICAL",
                title="Pedestrians/Victims Near Collision",
                description=f"{pedestrian_count} pedestrian(s) identified in immediate proximity of crash scene.",
                confidence=0.90
            ))

        return alerts

    def _generate_scene_summary(
        self,
        vehicles: int,
        pedestrians: int,
        fire: bool,
        smoke: bool,
        accident: bool,
        alerts: List[HazardAlert]
    ) -> str:
        """Constructs human-readable scene summary."""
        parts = [f"Detected {vehicles} vehicle(s) and {pedestrians} pedestrian(s)."]
        if accident: parts.append("CRITICAL: Vehicle collision identified.")
        if fire: parts.append("CRITICAL: Active fire detected.")
        if smoke: parts.append("WARNING: Heavy smoke observed.")
        if not alerts: parts.append("Scene clear of major active hazards.")
        return " ".join(parts)
