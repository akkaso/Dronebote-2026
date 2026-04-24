"""Tests for the MockGPIO controller."""

import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from pi.gpio_controller import MockGPIO, MAX_PRESS_TIMEOUT


class TestMockGPIO:
    def setup_method(self):
        self.gpio = MockGPIO()

    def test_press_button_logs_press_and_release(self):
        self.gpio.press_button("forward", 0.01)
        actions = [e["action"] for e in self.gpio.log]
        assert "press" in actions
        assert "release" in actions

    def test_press_button_correct_name(self):
        self.gpio.press_button("left", 0.01)
        press_events = [e for e in self.gpio.log if e["action"] == "press"]
        assert press_events[0]["button"] == "left"

    def test_press_duration_clamped_to_max(self):
        self.gpio.press_button("forward", MAX_PRESS_TIMEOUT + 100)
        press_events = [e for e in self.gpio.log if e["action"] == "press"]
        assert press_events[0]["duration"] <= MAX_PRESS_TIMEOUT

    def test_press_duration_clamped_to_zero(self):
        self.gpio.press_button("forward", -1.0)
        press_events = [e for e in self.gpio.log if e["action"] == "press"]
        assert press_events[0]["duration"] == 0.0

    def test_stop_all_logs_event(self):
        self.gpio.stop_all()
        actions = [e["action"] for e in self.gpio.log]
        assert "stop_all" in actions

    def test_multiple_buttons(self):
        for btn in ["forward", "left", "right", "back"]:
            self.gpio.press_button(btn, 0.0)
        btns_pressed = [e["button"] for e in self.gpio.log if e["action"] == "press"]
        assert set(btns_pressed) == {"forward", "left", "right", "back"}

    def test_thread_safety(self):
        """Multiple threads pressing buttons simultaneously should not crash."""
        def press(btn):
            self.gpio.press_button(btn, 0.01)

        threads = [threading.Thread(target=press, args=(b,))
                   for b in ["forward", "left", "right"]]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        press_count = sum(1 for e in self.gpio.log if e["action"] == "press")
        assert press_count == 3

    def test_stop_all_clears_active(self):
        """stop_all should clear the active set."""
        self.gpio._active.add("forward")
        self.gpio.stop_all()
        assert len(self.gpio._active) == 0
