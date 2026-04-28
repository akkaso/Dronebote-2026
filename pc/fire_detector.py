"""
fire_detector.py – HSV-based fire image detection.

Detects the printed fire image placed on the competition floor by thresholding
orange/red/yellow hues in HSV colour space.  No proprietary models are used;
all processing is performed with OpenCV routines compiled from source.
"""

from __future__ import annotations

import cv2
import numpy as np
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class FireDetection:
    """Result of a single-frame fire detection pass."""
    detected: bool
    centroid: Optional[Tuple[int, int]]  # (x, y) pixel coords, None if not found
    area: float                          # largest matching contour area (px²)
    mask: Optional[np.ndarray]           # binary mask for debugging


class FireDetector:
    """
    Detects a fire image in a video frame using HSV colour thresholding.

    Parameters
    ----------
    config_path : str or Path
        Path to ``config.yaml``.
    """

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)["fire"]

        self._lower_orange = np.array(cfg["hsv_lower_orange"], dtype=np.uint8)
        self._upper_orange = np.array(cfg["hsv_upper_orange"], dtype=np.uint8)
        self._lower_red1   = np.array(cfg["hsv_lower_red1"],   dtype=np.uint8)
        self._upper_red1   = np.array(cfg["hsv_upper_red1"],   dtype=np.uint8)
        self._lower_red2   = np.array(cfg["hsv_lower_red2"],   dtype=np.uint8)
        self._upper_red2   = np.array(cfg["hsv_upper_red2"],   dtype=np.uint8)
        self._min_area: int = int(cfg["min_area"])
        self._confirm_frames: int = int(cfg["confirm_frames"])

        self._consecutive_detections: int = 0

    # ------------------------------------------------------------------
    def _build_mask(self, hsv: np.ndarray) -> np.ndarray:
        """Return a binary mask covering orange + red (wrap-around) regions."""
        mask_orange = cv2.inRange(hsv, self._lower_orange, self._upper_orange)
        mask_red1   = cv2.inRange(hsv, self._lower_red1,   self._upper_red1)
        mask_red2   = cv2.inRange(hsv, self._lower_red2,   self._upper_red2)
        combined    = cv2.bitwise_or(mask_orange, cv2.bitwise_or(mask_red1, mask_red2))

        # Morphological cleanup: remove noise and fill small holes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN,  kernel)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
        return combined

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> FireDetection:
        """
        Analyse a single BGR frame and return a :class:`FireDetection`.

        Parameters
        ----------
        frame : np.ndarray
            BGR image as returned by ``cv2.VideoCapture.read()``.

        Returns
        -------
        FireDetection
        """
        hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = self._build_mask(hsv)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            self._consecutive_detections = 0
            return FireDetection(detected=False, centroid=None, area=0.0, mask=mask)

        largest = max(contours, key=cv2.contourArea)
        area    = cv2.contourArea(largest)

        if area < self._min_area:
            self._consecutive_detections = 0
            return FireDetection(detected=False, centroid=None, area=area, mask=mask)

        # Compute centroid via image moments
        M = cv2.moments(largest)
        if M["m00"] == 0:
            self._consecutive_detections = 0
            return FireDetection(detected=False, centroid=None, area=area, mask=mask)

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        self._consecutive_detections += 1
        confirmed = self._consecutive_detections >= self._confirm_frames

        return FireDetection(
            detected=confirmed,
            centroid=(cx, cy),
            area=area,
            mask=mask,
        )

    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Reset the consecutive-frame counter (call between missions)."""
        self._consecutive_detections = 0
