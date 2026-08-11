"""
Vision Input Handlers

Implements handlers for image upload, video upload, and live RTSP/webcam stream inputs.
"""

import io
import time
import base64
import numpy as np
from typing import Any, Tuple, Optional, Generator, Callable, Union
from PIL import Image

from vision.bbox_utils import OPENCV_AVAILABLE
from utils.logger import app_logger

if OPENCV_AVAILABLE:
    import cv2


class ImageInputHandler:
    """Handler for image uploads (file path, bytes, base64, PIL Image, or NumPy array)."""

    @staticmethod
    def load_image(source: Any) -> Tuple[Optional[np.ndarray], int, int]:
        """
        Converts input source into standardized OpenCV BGR image array (h, w, 3).
        Returns (image_array, width, height).
        """
        if source is None:
            return None, 0, 0

        try:
            # 1. Already OpenCV NumPy array
            if isinstance(source, np.ndarray):
                h, w = source.shape[0], source.shape[1]
                return source.copy(), w, h

            # 2. PIL Image
            if isinstance(source, Image.Image):
                rgb_img = source.convert("RGB")
                np_img = np.array(rgb_img)
                # Convert RGB to BGR for OpenCV
                bgr_img = np_img[:, :, ::-1].copy()
                h, w = bgr_img.shape[0], bgr_img.shape[1]
                return bgr_img, w, h

            # 3. Raw Bytes
            if isinstance(source, bytes):
                if OPENCV_AVAILABLE:
                    nparr = np.frombuffer(source, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is not None:
                        return img, img.shape[1], img.shape[0]

                # Fallback to PIL
                pil_img = Image.open(io.BytesIO(source)).convert("RGB")
                np_img = np.array(pil_img)[:, :, ::-1].copy()
                return np_img, np_img.shape[1], np_img.shape[0]

            # 4. File Path or Base64 String
            if isinstance(source, str):
                # Base64 string
                if source.startswith("data:image") or len(source) > 500:
                    raw_b64 = source.split(",")[-1] if "," in source else source
                    img_bytes = base64.b64decode(raw_b64)
                    return ImageInputHandler.load_image(img_bytes)

                # File path
                if OPENCV_AVAILABLE:
                    img = cv2.imread(source)
                    if img is not None:
                        return img, img.shape[1], img.shape[0]

                pil_img = Image.open(source).convert("RGB")
                np_img = np.array(pil_img)[:, :, ::-1].copy()
                return np_img, np_img.shape[1], np_img.shape[0]

        except Exception as e:
            app_logger.error(f"[ImageInputHandler] Failed to load image source: {e}")

        # Default synthetic frame fallback if image read fails
        blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
        return blank_img, 640, 480


class VideoInputHandler:
    """Handler for video upload processing (file path or video stream)."""

    @staticmethod
    def extract_frames(
        video_path: str,
        frame_sample_rate: int = 5
    ) -> Generator[Tuple[int, np.ndarray, float], None, None]:
        """
        Yields sampled frames from video file.
        Yields (frame_index, frame_bgr_array, timestamp_sec).
        """
        if not OPENCV_AVAILABLE:
            app_logger.warning("[VideoInputHandler] OpenCV unavailable for video decoding.")
            yield 0, np.zeros((480, 640, 3), dtype=np.uint8), 0.0
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            app_logger.error(f"[VideoInputHandler] Unable to open video file: {video_path}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_idx = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_idx % frame_sample_rate == 0:
                    timestamp = frame_idx / fps
                    yield frame_idx, frame, timestamp

                frame_idx += 1
        finally:
            cap.release()


class LiveCameraInputHandler:
    """Handler for live camera feeds (webcam index or RTSP IP camera streams)."""

    @staticmethod
    def stream_camera(
        stream_url: Union[int, str] = 0,
        fps_limit: float = 10.0,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> Generator[Tuple[int, np.ndarray, float], None, None]:
        """
        Connects to RTSP/webcam stream and yields real-time frames.
        Yields (frame_seq, frame_bgr_array, timestamp).
        """
        if not OPENCV_AVAILABLE:
            app_logger.warning("[LiveCameraInputHandler] OpenCV unavailable for camera streaming.")
            yield 0, np.zeros((480, 640, 3), dtype=np.uint8), time.time()
            return

        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            app_logger.error(f"[LiveCameraInputHandler] Unable to open camera stream: {stream_url}")
            return

        frame_seq = 0
        min_interval = 1.0 / max(fps_limit, 1.0)
        last_time = time.time()

        try:
            while cap.isOpened():
                if stop_check and stop_check():
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                now = time.time()
                if now - last_time >= min_interval:
                    last_time = now
                    frame_seq += 1
                    yield frame_seq, frame, now

        finally:
            cap.release()
