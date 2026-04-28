"""
Tests for fire_detector.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Allow importing from the pc/ package root
sys.path.insert(0, str(Path(__file__).parent.parent))

from fire_detector import FireDetector, FireDetection

CONFIG = Path(__file__).parent.parent / "config.yaml"


@pytest.fixture()
def detector() -> FireDetector:
    return FireDetector(CONFIG)


# ── Helpers ───────────────────────────────────────────────────────────────

def _solid_bgr(bgr: tuple[int, int, int], h: int = 200, w: int = 200) -> np.ndarray:
    """Create a solid-colour BGR frame."""
    return np.full((h, w, 3), bgr, dtype=np.uint8)


def _frame_with_patch(
    bg_bgr: tuple[int, int, int],
    patch_bgr: tuple[int, int, int],
    patch_size: int = 80,
    frame_h: int = 200,
    frame_w: int = 200,
) -> np.ndarray:
    """Create a frame with a coloured square patch in the centre."""
    frame = _solid_bgr(bg_bgr, frame_h, frame_w)
    cy, cx = frame_h // 2, frame_w // 2
    half = patch_size // 2
    frame[cy - half : cy + half, cx - half : cx + half] = patch_bgr
    return frame


# ── Tests ─────────────────────────────────────────────────────────────────

class TestFireDetectorNoFire:
    def test_blue_frame_returns_not_detected(self, detector: FireDetector) -> None:
        frame = _solid_bgr((200, 50, 50))  # blue-ish in BGR
        result = detector.detect(frame)
        assert isinstance(result, FireDetection)
        assert not result.detected

    def test_green_frame_returns_not_detected(self, detector: FireDetector) -> None:
        frame = _solid_bgr((50, 200, 50))
        result = detector.detect(frame)
        assert not result.detected

    def test_no_fire_centroid_is_none(self, detector: FireDetector) -> None:
        # Pure blue in BGR (B=200, G=50, R=50) – not a fire colour
        frame = _solid_bgr((200, 50, 50))
        result = detector.detect(frame)
        assert result.centroid is None


class TestFireDetectorWithFire:
    def test_orange_patch_eventually_confirmed(self, detector: FireDetector) -> None:
        # Orange in BGR ≈ (0, 165, 255)
        frame = _frame_with_patch(
            bg_bgr=(50, 50, 200),
            patch_bgr=(0, 165, 255),
            patch_size=100,
        )
        # Feed enough frames to exceed confirm_frames (default 5)
        result = None
        for _ in range(10):
            result = detector.detect(frame)
        assert result is not None
        assert result.detected

    def test_centroid_near_frame_centre(self, detector: FireDetector) -> None:
        frame = _frame_with_patch(
            bg_bgr=(50, 50, 200),
            patch_bgr=(0, 165, 255),
            patch_size=100,
        )
        for _ in range(10):
            result = detector.detect(frame)

        assert result.centroid is not None
        cx, cy = result.centroid
        # Patch is centred at (100, 100); centroid should be close
        assert abs(cx - 100) < 20
        assert abs(cy - 100) < 20

    def test_area_positive_when_detected(self, detector: FireDetector) -> None:
        frame = _frame_with_patch(
            bg_bgr=(50, 50, 200),
            patch_bgr=(0, 165, 255),
            patch_size=100,
        )
        for _ in range(10):
            result = detector.detect(frame)
        assert result.area > 0


class TestFireDetectorReset:
    def test_reset_clears_consecutive_counter(self, detector: FireDetector) -> None:
        frame = _frame_with_patch(
            bg_bgr=(50, 50, 200),
            patch_bgr=(0, 165, 255),
            patch_size=100,
        )
        for _ in range(4):
            detector.detect(frame)
        detector.reset()
        # After reset a single orange frame should NOT be confirmed
        result = detector.detect(frame)
        assert not result.detected


class TestFireDetectionDataclass:
    def test_default_fields(self) -> None:
        fd = FireDetection(detected=False, centroid=None, area=0.0, mask=None)
        assert fd.detected is False
        assert fd.centroid is None
        assert fd.area == 0.0
        assert fd.mask is None
