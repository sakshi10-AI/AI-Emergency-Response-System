"""
Model Loader Factory and Registry

Provides centralized caching and creation of vision detectors.
Enables pluggable switching between YOLOv11 and custom vision models.
"""

from typing import Dict, Type, Optional
from vision.base_detector import BaseVisionDetector
from vision.yolo_detector import YOLOv11Detector
from utils.logger import app_logger


class ModelLoader:
    """Singleton registry and factory for managing computer vision detectors."""

    _instance: Optional["ModelLoader"] = None
    _detector_classes: Dict[str, Type[BaseVisionDetector]] = {
        "yolo": YOLOv11Detector,
        "yolov11": YOLOv11Detector,
    }
    _loaded_cache: Dict[str, BaseVisionDetector] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_detector_type(cls, name: str, detector_class: Type[BaseVisionDetector]):
        """Registers a custom detector backend class (e.g. RT-DETR, SAM)."""
        cls._detector_classes[name.lower()] = detector_class
        app_logger.info(f"[ModelLoader] Registered custom detector type: '{name.lower()}' -> {detector_class.__name__}")

    @classmethod
    def get_detector(
        cls,
        model_type: str = "yolo11",
        model_name: str = "yolo11n.pt",
        device: str = "cpu"
    ) -> BaseVisionDetector:
        """
        Retrieves or instantiates a vision detector from cache.
        """
        cache_key = f"{model_type.lower()}_{model_name}_{device}"
        if cache_key in cls._loaded_cache:
            return cls._loaded_cache[cache_key]

        target_class = cls._detector_classes.get(model_type.lower(), YOLOv11Detector)
        app_logger.info(f"[ModelLoader] Instantiating detector '{target_class.__name__}' with weights '{model_name}' on '{device}'...")

        detector_instance = target_class(model_name=model_name, device=device)
        cls._loaded_cache[cache_key] = detector_instance
        return detector_instance

    @classmethod
    def clear_cache(cls):
        """Clears detector instance cache."""
        cls._loaded_cache.clear()


model_loader = ModelLoader()
