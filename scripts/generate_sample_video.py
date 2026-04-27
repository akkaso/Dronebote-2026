#!/usr/bin/env python3
"""
Genera un piccolo video MP4 sintetico con un blob arancione simile al fuoco
e un marker ArUco, per testare DroneBot 2026 senza una telecamera reale.

Output: sample_video.mp4 (radice del progetto)
        pc/sample_frames/frame_000.jpg ... frame_009.jpg
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cv2
import numpy as np

# ── Configurazione ──────────────────────────────────────────────────
RADICE_REPO = Path(__file__).parent.parent
VIDEO_OUTPUT = RADICE_REPO / "sample_video.mp4"
DIR_FRAME_ESEMPIO = RADICE_REPO / "pc" / "sample_frames"

LARGHEZZA, ALTEZZA = 640, 480
FPS = 15
DURATA_SEC = 3          # durata totale del video
N_FRAME = FPS * DURATA_SEC

MARKER_ID = 0
MARKER_DIM_PX = 80
ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50


def disegna_blob_fuoco(frame: np.ndarray, cx: int, cy: int, raggio: int) -> np.ndarray:
    """Disegna un blob arancione/giallo simile al fuoco."""
    out = frame.copy()
    # Alone arancione esterno
    cv2.circle(out, (cx, cy), raggio, (0, 120, 255), -1)
    # Nucleo giallo interno
    cv2.circle(out, (cx, cy), raggio // 2, (0, 200, 255), -1)
    # Punta luminosa
    cv2.circle(out, (cx, cy - raggio // 3), raggio // 4, (0, 240, 255), -1)
    return out


def genera_patch_aruco(marker_id: int, dimensione: int) -> np.ndarray:
    """Restituisce una patch BGR con il marker ArUco richiesto."""
    dizionario = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID)
    marker_grigio = np.zeros((dimensione, dimensione), dtype=np.uint8)
    cv2.aruco.generateImageMarker(dizionario, marker_id, dimensione, marker_grigio, 1)
    return cv2.cvtColor(marker_grigio, cv2.COLOR_GRAY2BGR)


def costruisci_frame(idx: int, patch_aruco: np.ndarray) -> np.ndarray:
    """Costruisce un singolo frame video."""
    frame = np.zeros((ALTEZZA, LARGHEZZA, 3), dtype=np.uint8)
    frame[:] = (30, 30, 30)  # sfondo scuro

    # Il blob di fuoco oscilla orizzontalmente
    angolo = 2 * math.pi * idx / N_FRAME
    cx = int(LARGHEZZA / 2 + LARGHEZZA / 4 * math.sin(angolo))
    cy = ALTEZZA // 2
    raggio = 40 + int(10 * math.sin(angolo * 3))
    frame = disegna_blob_fuoco(frame, cx, cy, raggio)

    # Marker ArUco nell'angolo in alto a sinistra
    ms = patch_aruco.shape[0]
    frame[20 : 20 + ms, 20 : 20 + ms] = patch_aruco

    # Numero del frame
    cv2.putText(
        frame,
        f"Frame {idx:03d}",
        (10, ALTEZZA - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (180, 180, 180),
        1,
    )
    return frame


def main() -> None:
    patch_aruco = genera_patch_aruco(MARKER_ID, MARKER_DIM_PX)

    # ── Scrittura MP4 ───────────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(VIDEO_OUTPUT), fourcc, FPS, (LARGHEZZA, ALTEZZA))
    if not writer.isOpened():
        print(f"ERRORE: Impossibile aprire VideoWriter per {VIDEO_OUTPUT}", file=sys.stderr)
        sys.exit(1)

    for i in range(N_FRAME):
        writer.write(costruisci_frame(i, patch_aruco))
    writer.release()
    print(f"Scritti {N_FRAME} frame → {VIDEO_OUTPUT}")

    # ── Scrittura sample_frames/ ────────────────────────────────────
    DIR_FRAME_ESEMPIO.mkdir(parents=True, exist_ok=True)
    for i in range(10):
        idx = int(i * N_FRAME / 10)
        percorso = DIR_FRAME_ESEMPIO / f"frame_{i:03d}.jpg"
        cv2.imwrite(str(percorso), costruisci_frame(idx, patch_aruco))
    print(f"Scritti 10 frame di esempio → {DIR_FRAME_ESEMPIO}/")


if __name__ == "__main__":
    main()

