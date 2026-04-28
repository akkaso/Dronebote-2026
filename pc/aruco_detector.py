"""Rilevamento marker ArUco e stima della posa per DroneBot 2026."""

from __future__ import annotations

import cv2
import numpy as np

from pc.utils import get_logger

logger = get_logger(__name__)


class ArucoDetector:
    """
    Rileva marker ArUco e stima la loro posa.

    Parametri
    ---------
    dictionary_id : int
        Una delle costanti cv2.aruco.DICT_*.
    marker_length : float
        Lunghezza fisica del lato del marker stampato in metri.
    camera_matrix : np.ndarray oppure None
        Matrice intrinseca della telecamera 3×3.  Se None, la stima della posa viene saltata.
    dist_coeffs : np.ndarray oppure None
        Coefficienti di distorsione (1×5).
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

        self._dizionario = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self._parametri = cv2.aruco.DetectorParameters()
        self._rilevatore = cv2.aruco.ArucoDetector(self._dizionario, self._parametri)

    def detect(
        self, frame: np.ndarray
    ) -> tuple[list[np.ndarray], list[int], list[np.ndarray] | None, list[np.ndarray] | None]:
        """
        Rileva i marker in *frame*.

        Restituisce
        -----------
        corners : lista di array float32 (1,4,2)
        ids     : lista di int (ID dei marker)
        rvecs   : lista di vettori di rotazione (o None se non c'è matrice telecamera)
        tvecs   : lista di vettori di traslazione (o None se non c'è matrice telecamera)
        """
        grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self._rilevatore.detectMarkers(grigio)

        if ids is None:
            return [], [], None, None

        ids_lista = ids.flatten().tolist()

        rvecs, tvecs = None, None
        if self.camera_matrix is not None and len(corners) > 0:
            rvecs = []
            tvecs = []
            # Punti oggetto per un marker quadrato centrato nell'origine
            punti_oggetto = np.array([
                [-self.marker_length / 2,  self.marker_length / 2, 0],
                [ self.marker_length / 2,  self.marker_length / 2, 0],
                [ self.marker_length / 2, -self.marker_length / 2, 0],
                [-self.marker_length / 2, -self.marker_length / 2, 0],
            ], dtype=np.float32)
            for corner in corners:
                ok, rvec, tvec = cv2.solvePnP(
                    punti_oggetto, corner[0], self.camera_matrix, self.dist_coeffs
                )
                if ok:
                    rvecs.append(rvec)
                    tvecs.append(tvec)

        return corners, ids_lista, rvecs, tvecs

    def draw(
        self,
        frame: np.ndarray,
        corners: list[np.ndarray],
        ids: list[int],
        rvecs: list[np.ndarray] | None = None,
        tvecs: list[np.ndarray] | None = None,
    ) -> np.ndarray:
        """Disegna i marker rilevati (e gli assi se la posa è disponibile) su *frame*."""
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

