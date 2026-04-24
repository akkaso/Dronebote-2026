"""
DroneBot 2026 – PC vision client (main entry-point).

Usage
-----
python3 vision_client.py [OPTIONS]

Options
-------
--source SOURCE     Video source: RTSP URL, HTTP URL, file path, or int (camera index).
                    Falls back to sample_video.mp4 then pc/sample_frames/.
--ws WS_URL         WebSocket URL of the Pi server (default: ws://localhost:8765).
--mock              Use MockWSClient (no WebSocket connection).
--no-display        Disable OpenCV imshow window.
--debug             Save annotated frames to pc/debug/.
--config CONFIG     Path to config.yaml (default: pc/config.yaml).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

# Allow running as `python3 pc/vision_client.py` from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pc.aruco_detector import ArucoDetector
from pc.navigation import decide_command
from pc.pid import PIDController
from pc.utils import FPSTimer, get_logger
from pc.ws_client import MockWSClient, WSClient

logger = get_logger("vision_client")

# ──────────────────────────────────────────────────────
# Defaults (overridden by config.yaml)
# ──────────────────────────────────────────────────────
DEFAULTS = {
    "fire_hsv_lower": [0, 120, 120],
    "fire_hsv_upper": [30, 255, 255],
    "min_contour_area": 500,
    "pid_kp": 0.8,
    "pid_ki": 0.05,
    "pid_kd": 0.1,
    "pid_windup_limit": 300.0,
    "pid_output_limit": 500.0,
    "turn_threshold": 40,
    "base_duration": 0.3,
    "ws_url": "ws://localhost:8765",
    "camera_index": 0,
    "debug_save": True,
    "display": True,
}

THIS_DIR = Path(__file__).parent
SAMPLE_VIDEO = Path(__file__).parent.parent / "sample_video.mp4"
SAMPLE_FRAMES_DIR = THIS_DIR / "sample_frames"
DEBUG_DIR = THIS_DIR / "debug"


def load_config(path: str) -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(path) as f:
            loaded = yaml.safe_load(f) or {}
        cfg.update(loaded)
    except FileNotFoundError:
        logger.warning("Config not found at %s; using defaults.", path)
    return cfg


# ──────────────────────────────────────────────────────
# Video source helpers
# ──────────────────────────────────────────────────────

def open_video(source: str | int) -> cv2.VideoCapture | None:
    """Try to open *source*; return capture or None."""
    cap = cv2.VideoCapture(source)
    if cap.isOpened():
        return cap
    cap.release()
    return None


def fallback_capture() -> cv2.VideoCapture | None:
    """Try sample_video.mp4, then loop over sample_frames/."""
    if SAMPLE_VIDEO.exists() and SAMPLE_VIDEO.stat().st_size > 0:
        logger.info("Falling back to %s", SAMPLE_VIDEO)
        return open_video(str(SAMPLE_VIDEO))
    logger.warning("sample_video.mp4 not found or empty; using sample_frames/")
    return None  # caller will use static-frame mode


def load_sample_frames() -> list[np.ndarray]:
    """Load all image files from sample_frames/ sorted by name."""
    frames = []
    for p in sorted(SAMPLE_FRAMES_DIR.glob("*.jpg")) + sorted(SAMPLE_FRAMES_DIR.glob("*.png")):
        img = cv2.imread(str(p))
        if img is not None:
            frames.append(img)
    return frames


# ──────────────────────────────────────────────────────
# Fire detection
# ──────────────────────────────────────────────────────

def detect_fire(
    frame: np.ndarray,
    hsv_lower: list,
    hsv_upper: list,
    min_area: int,
) -> tuple[bool, tuple[int, int] | None, np.ndarray]:
    """
    Detect fire-like colours in *frame* using HSV thresholding + morphology.

    Returns
    -------
    detected   : bool
    centroid   : (cx, cy) pixel coords of largest blob, or None
    mask       : binary mask (for debug display)
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array(hsv_lower, dtype=np.uint8)
    upper = np.array(hsv_upper, dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)

    # Morphological clean-up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False, None, mask

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < min_area:
        return False, None, mask

    M = cv2.moments(largest)
    if M["m00"] == 0:
        return False, None, mask

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return True, (cx, cy), mask


# ──────────────────────────────────────────────────────
# Debug frame overlay
# ──────────────────────────────────────────────────────

def annotate_frame(
    frame: np.ndarray,
    fire_detected: bool,
    centroid: tuple[int, int] | None,
    command: dict,
    fps: float,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    out = frame.copy()
    h, w = out.shape[:2]

    # Fire centroid
    if fire_detected and centroid:
        cv2.circle(out, centroid, 15, (0, 0, 255), 3)
        cv2.line(out, (w // 2, 0), (w // 2, h), (255, 255, 0), 1)

    # Command overlay
    label = f"CMD: {command.get('cmd','?')} ({command.get('duration',0):.2f}s)"
    cv2.putText(out, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(out, f"FPS: {fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 2)

    if not fire_detected:
        cv2.putText(out, "NO FIRE", (w // 2 - 60, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)
    return out


def save_debug_frame(frame: np.ndarray, index: int) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / f"frame_{index:06d}.jpg"
    cv2.imwrite(str(path), frame)


# ──────────────────────────────────────────────────────
# Main async loop
# ──────────────────────────────────────────────────────

async def run(args: argparse.Namespace, cfg: dict) -> None:
    # Build WS client
    if args.mock:
        ws = MockWSClient()
    else:
        ws = WSClient(args.ws or cfg["ws_url"])
        await ws.connect()

    # PID
    pid = PIDController(
        kp=cfg["pid_kp"],
        ki=cfg["pid_ki"],
        kd=cfg["pid_kd"],
        windup_limit=cfg["pid_windup_limit"],
        output_limit=cfg["pid_output_limit"],
    )

    # ArUco detector (no camera matrix → no pose estimation in default mode)
    aruco = ArucoDetector()

    # Open video source
    cap = None
    static_frames: list[np.ndarray] = []
    static_idx = 0

    if args.source:
        # Try as int (camera index) first
        try:
            src: str | int = int(args.source)
        except (ValueError, TypeError):
            src = args.source
        cap = open_video(src)
    else:
        # Fall back to camera_index from config
        camera_idx = cfg.get("camera_index", 0)
        cap = open_video(camera_idx)

    if cap is None:
        cap = fallback_capture()

    if cap is None:
        static_frames = load_sample_frames()
        if not static_frames:
            logger.error("No video source available and no sample_frames found. Exiting.")
            await ws.close()
            return
        logger.info("Using %d static sample frames (looping).", len(static_frames))

    timer = FPSTimer()
    frame_idx = 0
    display = cfg.get("display", True) and not args.no_display
    debug_save = cfg.get("debug_save", True) or args.debug

    logger.info("Starting vision loop. Press 'q' to quit.")

    try:
        while True:
            # Grab frame
            if cap is not None:
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop
                    ok, frame = cap.read()
                if not ok:
                    logger.warning("Cannot read frame; stopping.")
                    break
            else:
                frame = static_frames[static_idx % len(static_frames)]
                static_idx += 1
                await asyncio.sleep(0.033)  # ~30 fps

            dt = timer.tick()
            h, w = frame.shape[:2]
            frame_centre_x = w // 2

            # Fire detection
            fire_detected, centroid, mask = detect_fire(
                frame,
                cfg["fire_hsv_lower"],
                cfg["fire_hsv_upper"],
                cfg["min_contour_area"],
            )

            # Lateral error: positive → fire is right of centre
            if fire_detected and centroid:
                error = centroid[0] - frame_centre_x
            else:
                error = 0.0
                pid.reset()

            pid_output = pid.update(error, dt)

            # Decide command
            command = decide_command(
                pid_output,
                fire_detected,
                turn_threshold=cfg["turn_threshold"],
                base_duration=cfg["base_duration"],
            )

            # ArUco (optional, for logging/future use)
            corners, ids, rvecs, tvecs = aruco.detect(frame)
            if ids:
                logger.debug("ArUco IDs detected: %s", ids)

            # Send command
            await ws.send_command(command)

            # Annotate and display/save
            annotated = annotate_frame(frame, fire_detected, centroid, command, timer.fps)
            if len(corners) > 0:
                annotated = aruco.draw(annotated, corners, ids)

            if display:
                cv2.imshow("DroneBot 2026 – PC Vision", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break

            if debug_save:
                save_debug_frame(annotated, frame_idx)

            frame_idx += 1
            await asyncio.sleep(0)  # yield to event loop

    finally:
        if cap is not None:
            cap.release()
        if display:
            cv2.destroyAllWindows()
        await ws.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DroneBot 2026 PC vision client")
    p.add_argument("--source", default=None, help="Video source (URL, file, camera index)")
    p.add_argument("--ws", default=None, help="WebSocket URL (ws://host:port)")
    p.add_argument("--mock", action="store_true", help="Use mock WS client")
    p.add_argument("--no-display", action="store_true", help="Disable OpenCV window")
    p.add_argument("--debug", action="store_true", help="Save debug frames")
    p.add_argument("--config", default=str(THIS_DIR / "config.yaml"), help="config.yaml path")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config(args.config)
    asyncio.run(run(args, cfg))
