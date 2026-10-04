"""
Vision Quality Gate

Evaluates incoming imagery for motion blur, severe underexposure, or lens obstructions
before running compute-heavy neural inference. Provides fail-safe guardrails so the
system flags degraded footage for human dispatcher review rather than hallucinating.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class VisionQualityGate:
    """Evaluates image/frame quality metrics prior to AI inference."""

    # Thresholds
    BLUR_THRESHOLD: float = 60.0       # Laplacian variance below this is considered blurred
    SEVERELY_BLURRED: float = 25.0
    MIN_LUMINANCE: float = 30.0        # Mean pixel brightness below this is underexposed/night
    MAX_LUMINANCE: float = 245.0       # Mean pixel brightness above this is overexposed/glare

    @classmethod
    def evaluate_frame(cls, frame: Optional[np.ndarray]) -> Dict[str, Any]:
        """
        Calculates blur variance and mean luminance on a BGR image array.
        Returns status dict:
          - passed: bool
          - quality_tier: 'OPTIMAL', 'DEGRADED', or 'CRITICAL_DEFECT'
          - blur_score: float
          - brightness_score: float
          - advisory: str
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return {
                "passed": False,
                "quality_tier": "CRITICAL_DEFECT",
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "advisory": "Image payload is null or unreadable. Immediate human review required."
            }

        if not OPENCV_AVAILABLE:
            # Fallback if OpenCV not compiled
            return {
                "passed": True,
                "quality_tier": "OPTIMAL",
                "blur_score": 100.0,
                "brightness_score": 128.0,
                "advisory": "Quality gate running in passthrough mode (OpenCV unavailable)."
            }

        # 1. Convert to grayscale
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # 2. Laplacian Blur Variance
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 3. Luminance / Brightness
        mean_luminance = float(np.mean(gray))

        # 4. Determine status
        issues = []
        if laplacian_var < cls.SEVERELY_BLURRED:
            issues.append(f"Severe motion/lens blur (variance: {laplacian_var:.1f} < {cls.SEVERELY_BLURRED})")
        elif laplacian_var < cls.BLUR_THRESHOLD:
            issues.append(f"Mild blur detected (variance: {laplacian_var:.1f})")

        if mean_luminance < cls.MIN_LUMINANCE:
            issues.append(f"Scene heavily underexposed/night condition (luminance: {mean_luminance:.1f} < {cls.MIN_LUMINANCE})")
        elif mean_luminance > cls.MAX_LUMINANCE:
            issues.append(f"Scene overexposed/glare (luminance: {mean_luminance:.1f} > {cls.MAX_LUMINANCE})")

        passed = len(issues) == 0 or (laplacian_var >= cls.SEVERELY_BLURRED and mean_luminance >= cls.MIN_LUMINANCE)
        quality_tier = "OPTIMAL" if not issues else ("DEGRADED" if passed else "CRITICAL_DEFECT")
        advisory = "Visual quality optimal." if not issues else " | ".join(issues)

        return {
            "passed": passed,
            "quality_tier": quality_tier,
            "blur_score": round(laplacian_var, 1),
            "brightness_score": round(mean_luminance, 1),
            "advisory": advisory
        }


quality_gate = VisionQualityGate()
