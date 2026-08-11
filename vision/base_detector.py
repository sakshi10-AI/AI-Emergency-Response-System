"""
Abstract Base Vision Detector Interface

Defines the modular contract for computer vision detectors, enabling seamless
swapping between YOLOv11, RT-DETR, Faster-RCNN, custom ONNX models, or heuristic fallbacks.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional
from vision.schemas import DetectedObject


class BaseVisionDetector(ABC):
    """
    Abstract interface for vision object detectors.
    All custom or alternative detector backends must inherit from this class.
    """

    def __init__(self, model_name: str, device: str = "cpu"):
        self._model_name = model_name
        self._device = device
        self._is_loaded = False

    @property
    def model_name(self) -> str:
        """Returns the name or identifier of the detector model."""
        return self._model_name

    @property
    def device(self) -> str:
        """Returns the current execution device ('cpu' or 'cuda')."""
        return self._device

    @property
    def is_loaded(self) -> bool:
        """Returns True if the underlying model weights are loaded and ready."""
        return self._is_loaded

    @abstractmethod
    def load_model(self, model_path: Optional[str] = None, device: Optional[str] = None) -> bool:
        """
        Loads model weights into memory/GPU.
        Returns True if successfully initialized, False otherwise.
        """
        pass

    @abstractmethod
    def predict(self, image: Any, confidence_threshold: float = 0.45) -> List[DetectedObject]:
        """
        Runs inference on an input image frame (NumPy array, OpenCV BGR image, or PIL Image).
        Returns a list of standardized `DetectedObject` instances.
        """
        pass

    @abstractmethod
    def supported_categories(self) -> List[str]:
        """Returns list of object categories supported by this detector."""
        pass
