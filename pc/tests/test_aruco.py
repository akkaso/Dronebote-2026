"""Test per il rilevatore ArUco (nessun hardware telecamera necessario)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import cv2
import numpy as np
import pytest
from pc.aruco_detector import ArucoDetector


def _crea_frame_aruco(marker_id: int = 0, dim_immagine: int = 300) -> np.ndarray:
    """Crea un frame BGR bianco con un marker ArUco incorporato."""
    dizionario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    img_marker = np.zeros((200, 200), dtype=np.uint8)
    cv2.aruco.generateImageMarker(dizionario, marker_id, 200, img_marker, 1)

    frame = np.ones((dim_immagine, dim_immagine, 3), dtype=np.uint8) * 255
    offset = (dim_immagine - 200) // 2
    frame[offset : offset + 200, offset : offset + 200] = cv2.cvtColor(
        img_marker, cv2.COLOR_GRAY2BGR
    )
    return frame


class TestArucoDetector:
    def test_nessun_marker_in_frame_vuoto(self):
        det = ArucoDetector()
        vuoto = np.ones((300, 300, 3), dtype=np.uint8) * 200
        corners, ids, rvecs, tvecs = det.detect(vuoto)
        assert len(ids) == 0
        assert rvecs is None

    def test_rileva_marker_incorporato(self):
        det = ArucoDetector()
        frame = _crea_frame_aruco(marker_id=0)
        corners, ids, rvecs, tvecs = det.detect(frame)
        assert 0 in ids

    def test_restituisce_id_marker_corretto(self):
        det = ArucoDetector()
        for mid in [0, 5, 10]:
            frame = _crea_frame_aruco(marker_id=mid)
            _, ids, _, _ = det.detect(frame)
            assert mid in ids, f"Atteso marker id {mid} ma ottenuto {ids}"

    def test_forma_corners(self):
        det = ArucoDetector()
        frame = _crea_frame_aruco(marker_id=0)
        corners, ids, _, _ = det.detect(frame)
        assert len(corners) == len(ids)
        for c in corners:
            assert c.shape == (1, 4, 2)

    def test_nessuna_posa_senza_matrice_telecamera(self):
        """Senza camera_matrix, la stima della posa deve essere saltata."""
        det = ArucoDetector(camera_matrix=None)
        frame = _crea_frame_aruco()
        _, ids, rvecs, tvecs = det.detect(frame)
        assert rvecs is None
        assert tvecs is None

    def test_posa_con_matrice_telecamera(self):
        """Con camera_matrix fornita, rvecs/tvecs devono essere restituiti."""
        dim = 300
        fx = fy = dim
        cx = cy = dim / 2
        matrice_cam = np.array(
            [[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64
        )
        det = ArucoDetector(camera_matrix=matrice_cam)
        frame = _crea_frame_aruco()
        _, ids, rvecs, tvecs = det.detect(frame)
        if ids:  # marker trovato
            assert rvecs is not None
            assert tvecs is not None

    def test_draw_non_crasha(self):
        det = ArucoDetector()
        frame = _crea_frame_aruco()
        corners, ids, rvecs, tvecs = det.detect(frame)
        out = det.draw(frame, corners, ids, rvecs, tvecs)
        assert out.shape == frame.shape

    def test_draw_su_frame_vuoto(self):
        det = ArucoDetector()
        vuoto = np.ones((200, 200, 3), dtype=np.uint8) * 128
        out = det.draw(vuoto, [], [], None, None)
        assert out.shape == vuoto.shape

