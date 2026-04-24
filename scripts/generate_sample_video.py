#!/usr/bin/env python3
"""
Generate a small synthetic MP4 video with a fire-like orange blob
and an ArUco marker, for testing DroneBot 2026 without a real camera.

Output: sample_video.mp4 (project root)
        pc/sample_frames/frame_000.jpg ... frame_009.jpg
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cv2
import numpy as np

# ── Configuration ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
OUTPUT_VIDEO = REPO_ROOT / "sample_video.mp4"
SAMPLE_FRAMES_DIR = REPO_ROOT / "pc" / "sample_frames"

WIDTH, HEIGHT = 640, 480
FPS = 15
DURATION_SEC = 3          # total video length
N_FRAMES = FPS * DURATION_SEC

MARKER_ID = 0
MARKER_SIZE_PX = 80
ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50


def draw_fire_blob(frame: np.ndarray, cx: int, cy: int, radius: int) -> np.ndarray:
    """Draw an orange/yellow fire-like blob."""
    out = frame.copy()
    # Outer orange
    cv2.circle(out, (cx, cy), radius, (0, 120, 255), -1)
    # Inner yellow core
    cv2.circle(out, (cx, cy), radius // 2, (0, 200, 255), -1)
    # Bright tip
    cv2.circle(out, (cx, cy - radius // 3), radius // 4, (0, 240, 255), -1)
    return out


def generate_aruco_patch(marker_id: int, size: int) -> np.ndarray:
    """Return a BGR patch with the requested ArUco marker."""
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID)
    marker_gray = np.zeros((size, size), dtype=np.uint8)
    cv2.aruco.generateImageMarker(dictionary, marker_id, size, marker_gray, 1)
    return cv2.cvtColor(marker_gray, cv2.COLOR_GRAY2BGR)


def build_frame(idx: int, aruco_patch: np.ndarray) -> np.ndarray:
    """Build one video frame."""
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:] = (30, 30, 30)  # dark background

    # Fire blob oscillates horizontally
    angle = 2 * math.pi * idx / N_FRAMES
    cx = int(WIDTH / 2 + WIDTH / 4 * math.sin(angle))
    cy = HEIGHT // 2
    radius = 40 + int(10 * math.sin(angle * 3))
    frame = draw_fire_blob(frame, cx, cy, radius)

    # ArUco marker in top-left corner
    ms = aruco_patch.shape[0]
    frame[20 : 20 + ms, 20 : 20 + ms] = aruco_patch

    # Frame number text
    cv2.putText(
        frame,
        f"Frame {idx:03d}",
        (10, HEIGHT - 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (180, 180, 180),
        1,
    )
    return frame


def main() -> None:
    aruco_patch = generate_aruco_patch(MARKER_ID, MARKER_SIZE_PX)

    # ── Write MP4 ──────────────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUTPUT_VIDEO), fourcc, FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        print(f"ERROR: Cannot open VideoWriter for {OUTPUT_VIDEO}", file=sys.stderr)
        sys.exit(1)

    for i in range(N_FRAMES):
        writer.write(build_frame(i, aruco_patch))
    writer.release()
    print(f"Wrote {N_FRAMES} frames → {OUTPUT_VIDEO}")

    # ── Write sample_frames/ ───────────────────────────────────────
    SAMPLE_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(10):
        idx = int(i * N_FRAMES / 10)
        path = SAMPLE_FRAMES_DIR / f"frame_{i:03d}.jpg"
        cv2.imwrite(str(path), build_frame(idx, aruco_patch))
    print(f"Wrote 10 sample frames → {SAMPLE_FRAMES_DIR}/")


if __name__ == "__main__":
    main()
