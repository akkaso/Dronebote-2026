"""ArUco marker detection and pose estimation for DroneBot 2026."""

from __future__ import annotations

import cv2
import numpy as np

from pc.utils import get_logger

logger = get_logger(__name__)


class ArucoDetector:
    """
    Detect ArUco markers and estimate their pose.

    Parameters
    ----------
    dictionary_id : int
        One of the cv2.aruco.DICT_* constants.
    marker_length : float
        Physical side length of the printed marker in metres.
    camera_matrix : np.ndarray or None
        3×3 intrinsic camera matrix.  If None, pose estimation is skipped.
    dist_coeffs : np.ndarray or None
        Distortion coefficients (1×5).
    """

    def __init__(
        self,
        dictionary_id: int = cv2.aruco.DICT_4X4_50,
        marker_length: float = 0.05,
        camera_matrix: np.ndarray | None = None,
        dist_coeffs: np.ndarray | None = None,
    ) -> None:
        self.marker_length = marker_length
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs if dist_coeffs is not None else np.zeros((1, 5))

        self._dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self._params = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(self._dictionary, self._params)

    def detect(
        self, frame: np.ndarray
    ) -> tuple[list[np.ndarray], list[int], list[np.ndarray] | None, list[np.ndarray] | None]:
        """
        Detect markers in *frame*.

        Returns
        -------
        corners : list of (1,4,2) float32 arrays
        ids     : list of int (marker IDs)
        rvecs   : list of rotation vectors (or None if no camera matrix)
        tvecs   : list of translation vectors (or None if no camera matrix)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._detector.detectMarkers(gray)

        if ids is None:
            return [], [], None, None

        ids_flat = ids.flatten().tolist()

        rvecs, tvecs = None, None
        if self.camera_matrix is not None and len(corners) > 0:
            rvecs = []
            tvecs = []
            obj_pts = np.array([
                [-self.marker_length / 2,  self.marker_length / 2, 0],
                [ self.marker_length / 2,  self.marker_length / 2, 0],
                [ self.marker_length / 2, -self.marker_length / 2, 0],
                [-self.marker_length / 2, -self.marker_length / 2, 0],
            ], dtype=np.float32)
            for corner in corners:
                ok, rvec, tvec = cv2.solvePnP(
                    obj_pts, corner[0], self.camera_matrix, self.dist_coeffs
                )
                if ok:
                    rvecs.append(rvec)
                    tvecs.append(tvec)

        return corners, ids_flat, rvecs, tvecs

    def draw(
        self,
        frame: np.ndarray,
        corners: list[np.ndarray],
        ids: list[int],
        rvecs: list[np.ndarray] | None = None,
        tvecs: list[np.ndarray] | None = None,
    ) -> np.ndarray:
        """Draw detected markers (and axes if pose available) onto *frame*."""
        out = frame.copy()
        if len(corners) > 0:
            cv2.aruco.drawDetectedMarkers(out, corners, np.array(ids))
            if rvecs is not None and tvecs is not None and self.camera_matrix is not None:
                for rvec, tvec in zip(rvecs, tvecs):
                    cv2.drawFrameAxes(
                        out,
                        self.camera_matrix,
                        self.dist_coeffs,
                        rvec,
                        tvec,
                        self.marker_length * 0.5,
                    )
        return out
