"""
GPIO controller for DroneBot 2026 (Pi side).

Provides
--------
- ``RealGPIO``  – uses RPi.GPIO (only works on a Raspberry Pi)
- ``MockGPIO``  – thread-safe stub for testing without hardware
- ``get_controller(mock=False)`` – factory function

Both classes expose:
    press_button(button: str, duration: float) -> None
    stop_all() -> None
"""

from __future__ import annotations

import threading
import time
import logging

logger = logging.getLogger(__name__)

# ── Button → GPIO BCM pin mapping ────────────────────────────────────
BUTTON_PINS: dict[str, int] = {
    "forward": 17,
    "left":    27,
    "right":   22,
    "back":    10,
    "stop":     9,  # optional dedicated stop button
}

# Maximum time (seconds) a single button press can be held
MAX_PRESS_TIMEOUT: float = 5.0


class MockGPIO:
    """
    Thread-safe mock GPIO controller for tests and development.

    Records all calls in ``self.log`` so tests can assert on behaviour.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.log: list[dict] = []
        self._active: set[str] = set()
        logger.info("MockGPIO initialised.")

    def press_button(self, button: str, duration: float) -> None:
        """
        Simulate pressing *button* for *duration* seconds.

        Clamps *duration* to [0, MAX_PRESS_TIMEOUT].
        Thread-safe: only one button active at a time.
        """
        duration = max(0.0, min(duration, MAX_PRESS_TIMEOUT))
        with self._lock:
            logger.info("[MockGPIO] press_button(%s, %.3fs)", button, duration)
            self._active.add(button)
            self.log.append({"action": "press", "button": button, "duration": duration})

        time.sleep(duration)

        with self._lock:
            self._active.discard(button)
            self.log.append({"action": "release", "button": button})

    def stop_all(self) -> None:
        """Simulate releasing all buttons immediately."""
        with self._lock:
            logger.info("[MockGPIO] stop_all")
            self._active.clear()
            self.log.append({"action": "stop_all"})


class RealGPIO:
    """
    Real RPi.GPIO controller.

    Requires the ``RPi.GPIO`` package (available on a Raspberry Pi).
    Raises ``ImportError`` if not running on supported hardware.
    """

    def __init__(self) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "RPi.GPIO is not available. Run with --mock on non-Pi hardware."
            ) from exc

        self._GPIO = GPIO
        self._lock = threading.Lock()

        GPIO.setmode(GPIO.BCM)
        for pin in BUTTON_PINS.values():
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        logger.info("RealGPIO initialised (BCM mode).")

    def _set_pin(self, button: str, state: bool) -> None:
        pin = BUTTON_PINS.get(button)
        if pin is None:
            logger.warning("Unknown button: %s", button)
            return
        self._GPIO.output(pin, self._GPIO.HIGH if state else self._GPIO.LOW)

    def press_button(self, button: str, duration: float) -> None:
        """
        Press *button* GPIO pin HIGH for *duration* seconds, then release.

        Thread-safe, duration clamped to MAX_PRESS_TIMEOUT.
        """
        duration = max(0.0, min(duration, MAX_PRESS_TIMEOUT))
        with self._lock:
            logger.info("[RealGPIO] press_button(%s, %.3fs)", button, duration)
            self._set_pin(button, True)

        time.sleep(duration)

        with self._lock:
            self._set_pin(button, False)

    def stop_all(self) -> None:
        """Set all GPIO pins LOW immediately."""
        with self._lock:
            logger.info("[RealGPIO] stop_all")
            for button in BUTTON_PINS:
                self._set_pin(button, False)

    def cleanup(self) -> None:
        """Release GPIO resources (call on shutdown)."""
        self.stop_all()
        self._GPIO.cleanup()


def get_controller(mock: bool = False) -> MockGPIO | RealGPIO:
    """Return a MockGPIO or RealGPIO depending on *mock* flag."""
    if mock:
        return MockGPIO()
    return RealGPIO()
