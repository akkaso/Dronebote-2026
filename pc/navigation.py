"""Convert PID output to discrete DroneBot commands."""

from __future__ import annotations

from pc.pid import PIDController
from pc.utils import get_logger

logger = get_logger(__name__)

# Discrete command constants
CMD_FORWARD = "forward"
CMD_LEFT = "left"
CMD_RIGHT = "right"
CMD_STOP = "stop"

# Default thresholds (pixels of lateral error)
DEFAULT_TURN_THRESHOLD = 40   # below this → go straight
DEFAULT_BASE_DURATION = 0.3   # seconds per command

# Maximum PID output mapped to this max duration (seconds)
MAX_DURATION = 1.5


def decide_command(
    pid_output: float,
    fire_detected: bool,
    pid: PIDController | None = None,
    turn_threshold: float = DEFAULT_TURN_THRESHOLD,
    base_duration: float = DEFAULT_BASE_DURATION,
) -> dict:
    """
    Convert *pid_output* (lateral correction signal) into a command dict.

    Parameters
    ----------
    pid_output      : float — raw PID output (positive → fire is right of centre)
    fire_detected   : bool  — whether fire was found in the frame
    pid             : unused, kept for API compatibility
    turn_threshold  : float — |pid_output| below this → go forward
    base_duration   : float — minimum command duration in seconds

    Returns
    -------
    dict with keys ``cmd`` (str) and ``duration`` (float, seconds)
    """
    if not fire_detected:
        return {"cmd": CMD_STOP, "duration": 0.0}

    abs_out = abs(pid_output)

    # Scale duration proportionally to the correction needed
    duration = base_duration + min(abs_out / 200.0, MAX_DURATION - base_duration)

    if abs_out < turn_threshold:
        cmd = CMD_FORWARD
    elif pid_output > 0:
        cmd = CMD_RIGHT
    else:
        cmd = CMD_LEFT

    logger.debug("decide_command: pid_out=%.2f → %s %.2fs", pid_output, cmd, duration)
    return {"cmd": cmd, "duration": round(duration, 3)}
