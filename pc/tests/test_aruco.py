"""Tests for the ArUco detector (no camera hardware required)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import cv2
import numpy as np
import pytest
from pc.aruco_detector import ArucoDetector


def _make_aruco_frame(marker_id: int = 0, img_size: int = 300) -> np.ndarray:
    """Create a white BGR frame with one ArUco marker embedded."""
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_img = np.zeros((200, 200), dtype=np.uint8)
    cv2.aruco.generateImageMarker(dictionary, marker_id, 200, marker_img, 1)

    frame = np.ones((img_size, img_size, 3), dtype=np.uint8) * 255
    offset = (img_size - 200) // 2
    frame[offset : offset + 200, offset : offset + 200] = cv2.cvtColor(
        marker_img, cv2.COLOR_GRAY2BGR
    )
    return frame


class TestArucoDetector:
    def test_no_marker_in_blank_frame(self):
        det = ArucoDetector()
        blank = np.ones((300, 300, 3), dtype=np.uint8) * 200
        corners, ids, rvecs, tvecs = det.detect(blank)
        assert len(ids) == 0
        assert rvecs is None

    def test_detects_embedded_marker(self):
        det = ArucoDetector()
        frame = _make_aruco_frame(marker_id=0)
        corners, ids, rvecs, tvecs = det.detect(frame)
        assert 0 in ids

    def test_returns_correct_marker_id(self):
        det = ArucoDetector()
        for mid in [0, 5, 10]:
            frame = _make_aruco_frame(marker_id=mid)
            _, ids, _, _ = det.detect(frame)
            assert mid in ids, f"Expected marker id {mid} but got {ids}"

    def test_corners_shape(self):
        det = ArucoDetector()
        frame = _make_aruco_frame(marker_id=0)
        corners, ids, _, _ = det.detect(frame)
        assert len(corners) == len(ids)
        for c in corners:
            assert c.shape == (1, 4, 2)

    def test_no_pose_without_camera_matrix(self):
        """Without camera_matrix, pose estimation should be skipped."""
        det = ArucoDetector(camera_matrix=None)
        frame = _make_aruco_frame()
        _, ids, rvecs, tvecs = det.detect(frame)
        assert rvecs is None
        assert tvecs is None

    def test_pose_with_camera_matrix(self):
        """With camera_matrix provided, rvecs/tvecs should be returned."""
        img_size = 300
        fx = fy = img_size
        cx = cy = img_size / 2
        camera_matrix = np.array(
            [[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64
        )
        det = ArucoDetector(camera_matrix=camera_matrix)
        frame = _make_aruco_frame()
        _, ids, rvecs, tvecs = det.detect(frame)
        if ids:  # marker was found
            assert rvecs is not None
            assert tvecs is not None

    def test_draw_does_not_crash(self):
        det = ArucoDetector()
        frame = _make_aruco_frame()
        corners, ids, rvecs, tvecs = det.detect(frame)
        out = det.draw(frame, corners, ids, rvecs, tvecs)
        assert out.shape == frame.shape

    def test_draw_on_empty(self):
        det = ArucoDetector()
        blank = np.ones((200, 200, 3), dtype=np.uint8) * 128
        out = det.draw(blank, [], [], None, None)
        assert out.shape == blank.shape
