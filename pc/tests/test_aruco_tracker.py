"""
Tests for aruco_tracker.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from aruco_tracker import ArucoTracker, ArucoDetection

CONFIG = Path(__file__).parent.parent / "config.yaml"


@pytest.fixture()
def tracker() -> ArucoTracker:
    return ArucoTracker(CONFIG)


# ── Helpers ───────────────────────────────────────────────────────────────

def _blank_frame(h: int = 480, w: int = 640) -> np.ndarray:
    """Return a white BGR frame."""
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _frame_with_aruco(
    marker_id: int = 1,
    dict_name: str = "DICT_5X5_100",
    frame_h: int = 480,
    frame_w: int = 640,
    marker_size: int = 100,
    offset_x: int = 0,
    offset_y: int = 0,
) -> np.ndarray:
    """
    Render an ArUco marker centred at (frame_cx + offset_x, frame_cy + offset_y).
    """
    dict_id = cv2.aruco.DICT_5X5_100
    aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)

    frame = _blank_frame(frame_h, frame_w)
    cx = frame_w // 2 + offset_x
    cy = frame_h // 2 + offset_y
    x0 = cx - marker_size // 2
    y0 = cy - marker_size // 2
    x1 = x0 + marker_size
    y1 = y0 + marker_size

    # Clip to frame bounds
    x0c, y0c = max(x0, 0), max(y0, 0)
    x1c, y1c = min(x1, frame_w), min(y1, frame_h)
    mx0, my0 = x0c - x0, y0c - y0
    mx1, my1 = mx0 + (x1c - x0c), my0 + (y1c - y0c)

    frame[y0c:y1c, x0c:x1c] = cv2.cvtColor(
        marker_img[my0:my1, mx0:mx1], cv2.COLOR_GRAY2BGR
    )
    return frame


# ── Tests ─────────────────────────────────────────────────────────────────

class TestArucoTrackerNoMarker:
    def test_blank_frame_not_detected(self, tracker: ArucoTracker) -> None:
        frame = _blank_frame()
        result = tracker.detect(frame)
        assert isinstance(result, ArucoDetection)
        assert not result.detected

    def test_blank_frame_zero_offsets(self, tracker: ArucoTracker) -> None:
        frame = _blank_frame()
        result = tracker.detect(frame)
        assert result.offset_x == 0
        assert result.offset_y == 0

    def test_blank_frame_no_centroid(self, tracker: ArucoTracker) -> None:
        frame = _blank_frame()
        result = tracker.detect(frame)
        assert result.centroid is None


class TestArucoTrackerWithMarker:
    def test_centred_marker_detected(self, tracker: ArucoTracker) -> None:
        frame = _frame_with_aruco(marker_id=1)
        result = tracker.detect(frame)
        assert result.detected

    def test_centred_marker_id_correct(self, tracker: ArucoTracker) -> None:
        frame = _frame_with_aruco(marker_id=1)
        result = tracker.detect(frame)
        assert result.marker_id == 1

    def test_centred_marker_offset_within_dead_band(self, tracker: ArucoTracker) -> None:
        """Marker at frame centre → offsets should be 0 (within dead-band)."""
        frame = _frame_with_aruco(marker_id=1, offset_x=0, offset_y=0)
        result = tracker.detect(frame)
        # dead_band is 20px; a perfectly centred marker should produce 0
        assert result.offset_x == 0
        assert result.offset_y == 0

    def test_offset_right(self, tracker: ArucoTracker) -> None:
        """Marker shifted 80 px right → positive offset_x."""
        frame = _frame_with_aruco(marker_id=1, offset_x=80, offset_y=0)
        result = tracker.detect(frame)
        if result.detected:
            assert result.offset_x > 0

    def test_offset_left(self, tracker: ArucoTracker) -> None:
        """Marker shifted 80 px left → negative offset_x."""
        frame = _frame_with_aruco(marker_id=1, offset_x=-80, offset_y=0)
        result = tracker.detect(frame)
        if result.detected:
            assert result.offset_x < 0


class TestArucoTrackerLostFrames:
    def test_is_lost_after_limit(self, tracker: ArucoTracker) -> None:
        blank = _blank_frame()
        # Default lost_frames_limit is 10
        for _ in range(11):
            tracker.detect(blank)
        assert tracker.is_lost

    def test_not_lost_before_limit(self, tracker: ArucoTracker) -> None:
        blank = _blank_frame()
        for _ in range(5):
            tracker.detect(blank)
        assert not tracker.is_lost

    def test_reset_clears_lost_counter(self, tracker: ArucoTracker) -> None:
        blank = _blank_frame()
        for _ in range(11):
            tracker.detect(blank)
        tracker.reset()
        assert not tracker.is_lost


class TestArucoDetectionDataclass:
    def test_default_fields(self) -> None:
        ad = ArucoDetection(
            detected=False, offset_x=0, offset_y=0, marker_id=None, centroid=None
        )
        assert ad.detected is False
        assert ad.marker_id is None
