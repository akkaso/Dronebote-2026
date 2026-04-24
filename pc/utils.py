"""Shared utility helpers for the PC side."""

import logging
import time


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def clamp(value: float, low: float, high: float) -> float:
    """Clamp *value* to [low, high]."""
    return max(low, min(high, value))


class FPSTimer:
    """Simple helper to measure frames per second."""

    def __init__(self) -> None:
        self._last = time.monotonic()
        self.fps = 0.0

    def tick(self) -> float:
        """Call once per frame; returns current dt in seconds."""
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        self.fps = 1.0 / dt if dt > 0 else 0.0
        return dt
