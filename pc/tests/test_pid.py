"""Tests for the PID controller."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from pc.pid import PIDController


class TestPIDBasic:
    def test_proportional_only(self):
        """With ki=kd=0, output == kp * error."""
        pid = PIDController(kp=2.0, ki=0.0, kd=0.0)
        out = pid.update(10.0, dt=0.1)
        assert out == pytest.approx(20.0)

    def test_zero_error(self):
        pid = PIDController(kp=1.0, ki=1.0, kd=1.0)
        out = pid.update(0.0, dt=0.1)
        assert out == pytest.approx(0.0)

    def test_integral_accumulation(self):
        """Integral should accumulate over multiple steps."""
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
        pid.update(1.0, dt=0.1)  # integral = 0.1
        out = pid.update(1.0, dt=0.1)  # integral = 0.2
        assert out == pytest.approx(0.2)

    def test_derivative_term(self):
        """Derivative reacts to change in error."""
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0)
        pid.update(0.0, dt=0.1)   # prev_error = 0
        out = pid.update(10.0, dt=0.1)  # d = 10/0.1 = 100
        assert out == pytest.approx(100.0)

    def test_reset_clears_state(self):
        pid = PIDController(kp=0.0, ki=1.0, kd=1.0)
        pid.update(5.0, dt=1.0)
        pid.reset()
        out = pid.update(0.0, dt=1.0)
        assert out == pytest.approx(0.0)

    def test_output_limit(self):
        pid = PIDController(kp=10.0, output_limit=5.0)
        out = pid.update(100.0, dt=0.1)
        assert out == pytest.approx(5.0)

    def test_negative_output_limit(self):
        pid = PIDController(kp=10.0, output_limit=5.0)
        out = pid.update(-100.0, dt=0.1)
        assert out == pytest.approx(-5.0)

    def test_anti_windup(self):
        """Integral should be clamped at windup_limit."""
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0, windup_limit=10.0)
        # Feed large error for many steps
        for _ in range(1000):
            pid.update(100.0, dt=0.1)
        out = pid.update(0.0, dt=0.1)
        # output = ki * integral_clamped = 1.0 * 10.0
        assert abs(out) <= 10.0 + 1e-9

    def test_dt_zero_does_not_crash(self):
        pid = PIDController(kp=1.0)
        out = pid.update(5.0, dt=0.0)  # should not raise ZeroDivisionError
        assert isinstance(out, float)

    def test_negative_error(self):
        pid = PIDController(kp=1.0)
        out = pid.update(-7.5, dt=0.1)
        assert out == pytest.approx(-7.5)
