"""
Vision Module Pydantic Schemas

Defines strongly-typed schemas for bounding boxes, detected objects,
hazard alerts, and single-frame/video inference results.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Normalized or pixel bounding box coordinates [x_min, y_min, x_max, y_max]."""
    x_min: float = Field(..., description="Top-left X coordinate")
    y_min: float = Field(..., description="Top-left Y coordinate")
    x_max: float = Field(..., description="Bottom-right X coordinate")
    y_max: float = Field(..., description="Bottom-right Y coordinate")
    width: float = Field(..., description="Box width")
    height: float = Field(..., description="Box height")
    area: float = Field(..., description="Box area in pixels")


class DetectedObject(BaseModel):
    """Single detected object instance."""
    object_id: str = Field(..., description="Unique instance ID")
    class_id: int = Field(..., description="Model class integer ID")
    label: str = Field(..., description="Object label name (e.g. car, person, fire)")
    category: str = Field(..., description="Standard category: vehicle, pedestrian, accident, fire, smoke, hazard")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bbox: BoundingBox = Field(..., description="Bounding box location")


class HazardAlert(BaseModel):
    """Emergency hazard alert detected in frame."""
    hazard_id: str = Field(..., description="Unique hazard ID")
    hazard_type: str = Field(..., description="ACCIDENT, FIRE, SMOKE, PEDESTRIAN_IN_DANGER, STRUCTURAL_DAMAGE")
    risk_tier: str = Field(..., description="CRITICAL, HIGH, MODERATE, LOW")
    title: str = Field(..., description="Alert headline")
    description: str = Field(..., description="Detailed hazard description")
    confidence: float = Field(..., ge=0.0, le=1.0)
    associated_bbox: Optional[BoundingBox] = Field(default=None)


class VisionInferenceResult(BaseModel):
    """Complete inference output for a single image frame."""
    frame_id: str = Field(..., description="Unique frame identifier")
    timestamp: float = Field(..., description="Inference timestamp (epoch sec)")
    image_width: int = Field(..., description="Frame pixel width")
    image_height: int = Field(..., description="Frame pixel height")

    # Quantified Scene Counts
    detected_objects: List[DetectedObject] = Field(default_factory=list)
    vehicle_count: int = Field(default=0)
    pedestrian_count: int = Field(default=0)
    victim_count: int = Field(default=0)

    # Boolean Flag Indicators
    fire_detected: bool = Field(default=False)
    smoke_detected: bool = Field(default=False)
    accident_detected: bool = Field(default=False)

    # Hazard Assessments
    hazard_alerts: List[HazardAlert] = Field(default_factory=list)
    scene_summary: str = Field(..., description="Text summary of visual findings")

    # Technical Details
    processing_time_ms: float = Field(..., description="Total inference latency in milliseconds")
    model_used: str = Field(..., description="Model name/version used for detection")
    annotated_image_base64: Optional[str] = Field(default=None, description="Base64 encoded JPEG with drawn bounding boxes")


class VideoInferenceResult(BaseModel):
    """Aggregate output for processed video uploads or stream recordings."""
    source_name: str = Field(..., description="Video filename or stream URL")
    total_frames_processed: int
    duration_seconds: float
    fps: float
    max_vehicle_count: int
    max_pedestrian_count: int
    fire_detected_any_frame: bool
    smoke_detected_any_frame: bool
    accident_detected_any_frame: bool
    critical_alerts: List[HazardAlert] = Field(default_factory=list)
    overall_scene_summary: str
    frame_samples: List[VisionInferenceResult] = Field(default_factory=list)
