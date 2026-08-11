"""
Bounding Box Utilities and Visualizer

Provides NMS filtering, IoU calculation, sub-image cropping, base64 encoding,
and OpenCV frame visualization with custom category color palettes.
"""

import base64
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

from vision.schemas import BoundingBox, DetectedObject, HazardAlert
from utils.logger import app_logger

# Try importing cv2
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class BoundingBoxUtilities:
    """Helper utilities for bounding box geometry, NMS, and OpenCV visualization."""

    # Category BGR Color Palette for OpenCV
    CATEGORY_COLORS: Dict[str, Tuple[int, int, int]] = {
        "accident": (0, 0, 255),       # Bright Red
        "fire": (0, 128, 255),         # Bright Orange
        "smoke": (128, 128, 128),      # Gray
        "vehicle": (255, 191, 0),      # Deep Cyan / Blue-Green
        "pedestrian": (0, 255, 0),     # Bright Green
        "hazard": (255, 0, 255),       # Magenta / Purple
    }

    @staticmethod
    def calculate_iou(box1: BoundingBox, box2: BoundingBox) -> float:
        """Calculates Intersection-over-Union (IoU) between two bounding boxes."""
        x_left = max(box1.x_min, box2.x_min)
        y_top = max(box1.y_min, box2.y_min)
        x_right = min(box1.x_max, box2.x_max)
        y_bottom = min(box1.y_max, box2.y_max)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = box1.area
        box2_area = box2.area

        union_area = box1_area + box2_area - intersection_area
        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    @classmethod
    def apply_nms(cls, objects: List[DetectedObject], iou_threshold: float = 0.50) -> List[DetectedObject]:
        """Applies Non-Maximum Suppression (NMS) to filter redundant detections."""
        if not objects:
            return []

        # Sort by confidence descending
        sorted_objs = sorted(objects, key=lambda x: x.confidence, reverse=True)
        keep = []

        while sorted_objs:
            current = sorted_objs.pop(0)
            keep.append(current)

            remaining = []
            for obj in sorted_objs:
                iou = cls.calculate_iou(current.bbox, obj.bbox)
                if iou < iou_threshold or current.category != obj.category:
                    remaining.append(obj)
            sorted_objs = remaining

        return keep

    @classmethod
    def draw_bounding_boxes(
        cls,
        image: np.ndarray,
        objects: List[DetectedObject],
        hazard_alerts: Optional[List[HazardAlert]] = None
    ) -> np.ndarray:
        """
        Annotates OpenCV BGR image with bounding boxes, labels, confidence scores,
        and emergency alert overlays.
        """
        if not OPENCV_AVAILABLE or image is None or not isinstance(image, np.ndarray):
            return image

        annotated = image.copy()
        h, w = annotated.shape[0], annotated.shape[1]

        # Draw detected objects
        for obj in objects:
            bbox = obj.bbox
            color = cls.CATEGORY_COLORS.get(obj.category, (255, 255, 255))

            pt1 = (int(clamp(bbox.x_min, 0, w)), int(clamp(bbox.y_min, 0, h)))
            pt2 = (int(clamp(bbox.x_max, 0, w)), int(clamp(bbox.y_max, 0, h)))

            # Draw rectangle
            thickness = 3 if obj.category in ["accident", "fire"] else 2
            cv2.rectangle(annotated, pt1, pt2, color, thickness)

            # Label text
            label_str = f"{obj.label.upper()} {int(obj.confidence * 100)}%"
            (text_w, text_h), baseline = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            # Label background box
            label_pt1 = (pt1[0], max(0, pt1[1] - text_h - 6))
            label_pt2 = (pt1[0] + text_w + 6, max(text_h + 6, pt1[1]))
            cv2.rectangle(annotated, label_pt1, label_pt2, color, -1)

            # Label text overlay
            text_pos = (pt1[0] + 3, max(text_h + 2, pt1[1] - 4))
            cv2.putText(annotated, label_str, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        # Draw Hazard Alert Header Banner if critical alerts exist
        if hazard_alerts:
            banner_text = f"EMERGENCY ALERTS DETECTED: {len(hazard_alerts)}"
            cv2.rectangle(annotated, (0, 0), (w, 35), (0, 0, 200), -1)
            cv2.putText(annotated, banner_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        return annotated

    @staticmethod
    def crop_detection(image: np.ndarray, bbox: BoundingBox) -> Optional[np.ndarray]:
        """Crops sub-image area specified by bounding box."""
        if not OPENCV_AVAILABLE or image is None:
            return None

        h, w = image.shape[0], image.shape[1]
        x1, y1 = int(clamp(bbox.x_min, 0, w)), int(clamp(bbox.y_min, 0, h))
        x2, y2 = int(clamp(bbox.x_max, 0, w)), int(clamp(bbox.y_max, 0, h))

        if x2 > x1 and y2 > y1:
            return image[y1:y2, x1:x2].copy()
        return None

    @staticmethod
    def encode_image_to_base64(image: np.ndarray) -> Optional[str]:
        """Encodes OpenCV image array to base64 JPEG string."""
        if not OPENCV_AVAILABLE or image is None:
            return None

        try:
            success, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if success:
                return base64.b64encode(buffer).decode("utf-8")
        except Exception as e:
            app_logger.error(f"[bbox_utils] Error encoding image to base64: {e}")
        return None

    @staticmethod
    def decode_image_from_bytes(image_bytes: bytes) -> Optional[np.ndarray]:
        """Decodes raw image bytes into OpenCV BGR array."""
        if not OPENCV_AVAILABLE or not image_bytes:
            return None

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            app_logger.error(f"[bbox_utils] Error decoding image bytes: {e}")
        return None


def clamp(val: float, min_val: float, max_val: float) -> float:
    """Clamps a numeric value between min and max bounds."""
    return max(min_val, min(val, max_val))
