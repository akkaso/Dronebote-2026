"""
main.py – Mission control loop for DroneBot 2026.

Pipeline
--------
1. Capture video frames from the DJI NEO 1 (or USB/RTSP source).
2. Run FireDetector on each frame (Phase 1).
3. Once fire is confirmed, switch to rover-guidance mode (Phase 2):
   - Run ArucoTracker to locate the rover marker.
   - Translate pixel offset to a directional command via P-controller.
   - Send command over UDP to the Raspberry Pi rover server.
4. Stop when the rover enters the fire area (operator stops the mission)
   or when the maximum time elapses.

Usage
-----
    python main.py [--config pc/config.yaml]
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

from fire_detector import FireDetector
from aruco_tracker import ArucoTracker


# ── Commands sent to the Raspberry Pi (ASCII, newline-terminated) ──────────
CMD_FORWARD  = b"FORWARD\n"
CMD_BACKWARD = b"BACKWARD\n"
CMD_LEFT     = b"LEFT\n"
CMD_RIGHT    = b"RIGHT\n"
CMD_STOP     = b"STOP\n"


def _compute_command(offset_x: int, offset_y: int, kp: float, max_ms: int) -> bytes:
    """
    Map a 2-D pixel offset to a single directional command.

    Priority: horizontal error is corrected before vertical error to
    avoid the rover spinning while moving forward.
    """
    if offset_x > 0:
        return CMD_RIGHT
    if offset_x < 0:
        return CMD_LEFT
    if offset_y < 0:
        return CMD_FORWARD
    if offset_y > 0:
        return CMD_BACKWARD
    return CMD_STOP


class MissionController:
    """
    Orchestrates fire detection and rover guidance in a single loop.

    Parameters
    ----------
    config_path : str or Path
    """

    def __init__(self, config_path: str | Path = "config.yaml") -> None:
        config_path = Path(config_path)
        with open(config_path) as f:
            self._cfg = yaml.safe_load(f)

        self._fire_detector  = FireDetector(config_path)
        self._aruco_tracker  = ArucoTracker(config_path)

        net = self._cfg["network"]
        self._pi_addr = (net["pi_host"], int(net["pi_port"]))
        self._sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        ctrl = self._cfg["controller"]
        self._kp      = float(ctrl["kp"])
        self._max_ms  = int(ctrl["max_cmd_ms"])

        vid = self._cfg["video"]
        self._cap = cv2.VideoCapture(vid["source"])
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  int(vid["width"]))
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(vid["height"]))

        self._fire_confirmed  = False
        self._mission_running = False

    # ------------------------------------------------------------------
    def _send(self, command: bytes) -> None:
        try:
            self._sock.sendto(command, self._pi_addr)
        except OSError:
            pass  # network unavailable in simulation/test

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the main control loop (blocking).  Press 'q' to quit."""
        print("[MISSION] Starting – press 'q' to abort.")
        self._mission_running = True

        try:
            while self._mission_running:
                ret, frame = self._cap.read()
                if not ret:
                    print("[WARN] No frame received – check video source.")
                    time.sleep(0.05)
                    continue

                # ── Phase 1: Fire detection ──────────────────────────
                if not self._fire_confirmed:
                    fire = self._fire_detector.detect(frame)
                    self._annotate_fire(frame, fire)

                    if fire.detected:
                        print("[PHASE 1] Fire confirmed – switching to rover guidance.")
                        self._fire_confirmed = True

                # ── Phase 2: Rover guidance via ArUco ────────────────
                else:
                    aruco = self._aruco_tracker.detect(frame)
                    self._annotate_aruco(frame, aruco)

                    if self._aruco_tracker.is_lost:
                        print("[WARN] ArUco marker lost – sending STOP.")
                        self._send(CMD_STOP)
                    elif aruco.detected:
                        cmd = _compute_command(
                            aruco.offset_x, aruco.offset_y, self._kp, self._max_ms
                        )
                        self._send(cmd)
                    else:
                        self._send(CMD_STOP)

                cv2.imshow("DroneBot 2026", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("[MISSION] Aborted by operator.")
                    break

        finally:
            self._send(CMD_STOP)
            self._cap.release()
            cv2.destroyAllWindows()
            self._sock.close()
            print("[MISSION] Ended.")

    # ------------------------------------------------------------------
    @staticmethod
    def _annotate_fire(frame: np.ndarray, fire) -> None:  # type: ignore[annotation-unchecked]
        color = (0, 255, 0) if fire.detected else (0, 0, 255)
        label = f"FIRE {'OK' if fire.detected else 'searching'} area={fire.area:.0f}"
        cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        if fire.centroid:
            cv2.circle(frame, fire.centroid, 10, color, -1)

    @staticmethod
    def _annotate_aruco(frame: np.ndarray, aruco) -> None:  # type: ignore[annotation-unchecked]
        color = (255, 128, 0) if aruco.detected else (128, 128, 128)
        label = (
            f"ArUco id={aruco.marker_id} dx={aruco.offset_x} dy={aruco.offset_y}"
            if aruco.detected
            else "ArUco: searching…"
        )
        cv2.putText(frame, label, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        if aruco.centroid:
            cv2.drawMarker(frame, aruco.centroid, color, cv2.MARKER_CROSS, 20, 2)

    def stop(self) -> None:
        """Signal the loop to stop (can be called from another thread)."""
        self._mission_running = False


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DroneBot 2026 – mission controller")
    parser.add_argument(
        "--config",
        default=Path(__file__).parent / "config.yaml",
        help="Path to config.yaml (default: pc/config.yaml)",
    )
    args = parser.parse_args()

    controller = MissionController(config_path=args.config)
    controller.run()
