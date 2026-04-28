"""
Tests for rover_server.py (runs on any platform; GPIO calls are no-ops when
RPi.GPIO is unavailable).
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rover_server import RoverServer, COMMAND_PIN_MAP


# ── Fixtures ──────────────────────────────────────────────────────────────

def _free_port() -> int:
    """Return an available UDP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def server_port() -> int:
    return _free_port()


@pytest.fixture()
def running_server(server_port: int):
    """Start a RoverServer in a background thread and yield it."""
    srv = RoverServer(host="127.0.0.1", port=server_port, pulse_ms=50)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    time.sleep(0.1)  # give the server time to bind
    yield srv
    srv.stop()
    t.join(timeout=3)


def _send_udp(port: int, message: str) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(message.encode("ascii"), ("127.0.0.1", port))


# ── Tests ─────────────────────────────────────────────────────────────────

class TestCommandPinMap:
    def test_all_directions_mapped(self) -> None:
        for cmd in ("FORWARD", "BACKWARD", "LEFT", "RIGHT"):
            assert cmd in COMMAND_PIN_MAP

    def test_pins_are_unique(self) -> None:
        pins = list(COMMAND_PIN_MAP.values())
        assert len(pins) == len(set(pins))


class TestHandleCommand:
    def test_known_commands_do_not_raise(self) -> None:
        srv = RoverServer(host="127.0.0.1", port=_free_port(), pulse_ms=10)
        for cmd in ("FORWARD", "BACKWARD", "LEFT", "RIGHT", "STOP"):
            srv.handle_command(cmd)

    def test_unknown_command_does_not_raise(self) -> None:
        srv = RoverServer(host="127.0.0.1", port=_free_port(), pulse_ms=10)
        srv.handle_command("HOVER")

    def test_command_case_insensitive(self) -> None:
        srv = RoverServer(host="127.0.0.1", port=_free_port(), pulse_ms=10)
        srv.handle_command("forward")
        srv.handle_command("Forward")

    def test_command_strips_whitespace(self) -> None:
        srv = RoverServer(host="127.0.0.1", port=_free_port(), pulse_ms=10)
        srv.handle_command("  FORWARD\n")


class TestRoverServerNetwork:
    def test_server_starts_and_receives(self, running_server: RoverServer, server_port: int) -> None:
        _send_udp(server_port, "FORWARD\n")
        time.sleep(0.15)  # allow processing

    def test_server_receives_stop(self, running_server: RoverServer, server_port: int) -> None:
        _send_udp(server_port, "STOP\n")
        time.sleep(0.1)

    def test_server_receives_multiple_commands(
        self, running_server: RoverServer, server_port: int
    ) -> None:
        for cmd in ("FORWARD\n", "LEFT\n", "RIGHT\n", "BACKWARD\n", "STOP\n"):
            _send_udp(server_port, cmd)
            time.sleep(0.07)

    def test_server_stop_method(self, running_server: RoverServer) -> None:
        running_server.stop()
        # Should not raise; server will exit gracefully


class TestRoverServerInit:
    def test_default_host_and_port(self) -> None:
        port = _free_port()
        srv = RoverServer(port=port)
        assert srv._host == "0.0.0.0"
        assert srv._port == port

    def test_custom_pulse_ms(self) -> None:
        srv = RoverServer(port=_free_port(), pulse_ms=300)
        assert srv._pulse_ms == 300
