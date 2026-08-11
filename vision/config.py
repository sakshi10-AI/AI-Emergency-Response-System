"""
Vision Module Configuration Settings

Defines model weights, confidence thresholds, detection class maps,
device settings, and stream processing parameters.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class VisionConfig(BaseModel):
    """Configuration settings for Vision Module & YOLOv11 detectors."""

    # Model Settings
    model_name: str = Field(default="yolo11n.pt", description="YOLO model checkpoint name or path")
    custom_weights_path: Optional[str] = Field(default=None, description="Path to fine-tuned custom weights")
    device: str = Field(default="cpu", description="Execution device: 'cpu' or 'cuda'")

    # Detection Thresholds
    confidence_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="Minimum detection confidence score")
    nms_iou_threshold: float = Field(default=0.50, ge=0.0, le=1.0, description="Non-Maximum Suppression IoU threshold")
    max_detections_per_frame: int = Field(default=100, description="Maximum objects to return per frame")

    # Image / Frame Processing
    input_image_size: int = Field(default=640, description="Square image resize dimension for model input")
    frame_sample_rate: int = Field(default=5, description="Process 1 out of N frames for video streams")

    # Class ID to Category Map
    # Map standard COCO class IDs + custom emergency classes to standardized categories
    category_map: Dict[int, str] = Field(
        default={
            0: "pedestrian",      # person
            1: "vehicle",         # bicycle
            2: "vehicle",         # car
            3: "vehicle",         # motorcycle
            5: "vehicle",         # bus
            7: "vehicle",         # truck
            # Custom Emergency Fine-Tuned Class IDs (if fine-tuned model loaded)
            80: "accident",       # car crash / vehicle collision
            81: "fire",           # active flame
            82: "smoke",          # smoke plume
            83: "hazard",         # structural debris
        }
    )

    # Emergency Class Keywords for Text-based/CV label matching
    accident_keywords: List[str] = Field(default=["accident", "crash", "collision", "overturned"])
    fire_keywords: List[str] = Field(default=["fire", "flame", "blaze", "burning"])
    smoke_keywords: List[str] = Field(default=["smoke", "plume", "fumes"])
    vehicle_keywords: List[str] = Field(default=["car", "truck", "bus", "motorcycle", "vehicle", "automobile"])
    pedestrian_keywords: List[str] = Field(default=["person", "pedestrian", "victim", "bystander", "crowd"])


vision_config = VisionConfig()
