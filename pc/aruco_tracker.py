"""
aruco_tracker.py – ArUco marker detection and offset estimation.

Locates the ArUco marker attached to the rover in each video frame and
returns the pixel offset of the marker centre from the frame centre.
The offset is used by the P-controller in main.py to generate rover
movement commands.
"""

from __future__ import annotations

import cv2
import numpy as np
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

# OpenCV ArUco API changed between versions; support both.
try:
    from cv2 import aruco as _aruco  # type: ignore
    _ARUCO_NEW_API = hasattr(_aruco, "getPredefinedDictionary")
except ImportError as exc:
    raise ImportError("opencv-contrib-python is required for ArUco support") from exc


@dataclass
class ArucoDetection:
    """Result of a single-frame ArUco detection pass."""
    detected: bool
    offset_x: int   # positive → marker is to the RIGHT of frame centre
    offset_y: int   # positive → marker is BELOW frame centre
    marker_id: Optional[int]
    centroid: Optional[Tuple[int, int]]  # (x, y) in pixel coords


class ArucoTracker:
    """
    Detects an ArUco marker in a video frame and computes its offset
    from the frame centre.

    Parameters
    ----------
    config_path : str or Path
        Path to ``config.yaml``.
    """

    _DICT_MAP: dict[str, int] = {
        "DICT_4X4_50":    cv2.aruco.DICT_4X4_50,
        "DICT_5X5_100":   cv2.aruco.DICT_5X5_100,
        "DICT_6X6_250":   cv2.aruco.DICT_6X6_250,
        "DICT_7X7_1000":  cv2.aruco.DICT_7X7_1000,
        "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
    }

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)["aruco"]

        dict_name: str = cfg["dictionary"]
        if dict_name not in self._DICT_MAP:
            raise ValueError(f"Unknown ArUco dictionary: {dict_name!r}")

        self._aruco_dict = cv2.aruco.getPredefinedDictionary(self._DICT_MAP[dict_name])
        self._detector_params = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(self._aruco_dict, self._detector_params)

        self._dead_band: int     = int(cfg["dead_band"])
        self._lost_limit: int    = int(cfg["lost_frames_limit"])
        self._lost_counter: int  = 0

    # ------------------------------------------------------------------
    def detect(self, frame: np.ndarray) -> ArucoDetection:
        """
        Detect the ArUco marker in *frame* and compute the offset from
        the frame centre.

        Parameters
        ----------
        frame : np.ndarray
            BGR image.

        Returns
        -------
        ArucoDetection
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._detector.detectMarkers(gray)

        h, w = frame.shape[:2]
        frame_cx, frame_cy = w // 2, h // 2

        if ids is None or len(ids) == 0:
            self._lost_counter += 1
            return ArucoDetection(
                detected=False,
                offset_x=0,
                offset_y=0,
                marker_id=None,
                centroid=None,
            )

        self._lost_counter = 0

        # Use the first detected marker (teams use one marker per rover)
        corner = corners[0][0]  # shape (4, 2)
        cx = int(np.mean(corner[:, 0]))
        cy = int(np.mean(corner[:, 1]))

        raw_dx = cx - frame_cx
        raw_dy = cy - frame_cy

        # Apply dead-band to suppress jitter
        dx = raw_dx if abs(raw_dx) > self._dead_band else 0
        dy = raw_dy if abs(raw_dy) > self._dead_band else 0

        return ArucoDetection(
            detected=True,
            offset_x=dx,
            offset_y=dy,
            marker_id=int(ids[0][0]),
            centroid=(cx, cy),
        )

    # ------------------------------------------------------------------
    @property
    def is_lost(self) -> bool:
        """True when the marker has not been seen for ``lost_frames_limit`` frames."""
        return self._lost_counter >= self._lost_limit

    def reset(self) -> None:
        """Reset the lost-frame counter."""
        self._lost_counter = 0
