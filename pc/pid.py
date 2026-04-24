"""PID controller with anti-windup for DroneBot 2026."""

from pc.utils import clamp


class PIDController:
    """
    Discrete PID controller.

    Parameters
    ----------
    kp, ki, kd : float
        Proportional, integral, derivative gains.
    windup_limit : float
        Maximum absolute value of the integral accumulator (anti-windup).
    output_limit : float or None
        If set, clamp the final output to [-output_limit, output_limit].
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        windup_limit: float = 100.0,
        output_limit: float | None = None,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.windup_limit = windup_limit
        self.output_limit = output_limit

        self._integral: float = 0.0
        self._prev_error: float = 0.0

    def reset(self) -> None:
        """Reset internal state (call when switching targets)."""
        self._integral = 0.0
        self._prev_error = 0.0

    def update(self, error: float, dt: float) -> float:
        """
        Compute the PID output for *error* over time-step *dt* (seconds).

        Returns the control output (positive → turn right, negative → turn left
        in the navigation convention used by this project).
        """
        if dt <= 0:
            dt = 1e-6  # avoid division by zero

        # Proportional term
        p = self.kp * error

        # Integral term with anti-windup clamp
        self._integral += error * dt
        self._integral = clamp(self._integral, -self.windup_limit, self.windup_limit)
        i = self.ki * self._integral

        # Derivative term (backward difference)
        d = self.kd * (error - self._prev_error) / dt
        self._prev_error = error

        output = p + i + d
        if self.output_limit is not None:
            output = clamp(output, -self.output_limit, self.output_limit)
        return output
