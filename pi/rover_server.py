"""
rover_server.py – Raspberry Pi GPIO server for rover control.

Listens on a UDP socket for directional commands (ASCII strings) sent by
the PC control loop and maps each command to four GPIO output pins wired
to an Arduino that bypasses the RC transmitter push-buttons.

Pin mapping (BCM numbering, configurable):
    FORWARD  → GPIO 17
    BACKWARD → GPIO 27
    LEFT     → GPIO 22
    RIGHT    → GPIO 23

Each command activates the corresponding pin for PULSE_MS milliseconds,
then releases it.  A STOP command (or unknown command) releases all pins.

Usage
-----
    python rover_server.py [--host 0.0.0.0] [--port 5005] [--pulse-ms 200]
"""

from __future__ import annotations

import argparse
import socket
import time
import threading

# RPi.GPIO is only available on a Raspberry Pi.  Import with a graceful
# fallback so the module can be imported in tests on non-Pi hardware.
try:
    import RPi.GPIO as GPIO  # type: ignore
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    GPIO = None  # type: ignore
    _GPIO_AVAILABLE = False

# ── Default GPIO pin assignments (BCM numbering) ───────────────────────────
PIN_FORWARD  = 17
PIN_BACKWARD = 27
PIN_LEFT     = 22
PIN_RIGHT    = 23

ALL_PINS = (PIN_FORWARD, PIN_BACKWARD, PIN_LEFT, PIN_RIGHT)

COMMAND_PIN_MAP: dict[str, int] = {
    "FORWARD":  PIN_FORWARD,
    "BACKWARD": PIN_BACKWARD,
    "LEFT":     PIN_LEFT,
    "RIGHT":    PIN_RIGHT,
}


class RoverServer:
    """
    UDP server that maps text commands to GPIO pulses.

    Parameters
    ----------
    host : str
        Interface to bind to (default ``"0.0.0.0"``).
    port : int
        UDP port to listen on (default ``5005``).
    pulse_ms : int
        Duration in milliseconds to hold each GPIO pin HIGH.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5005,
        pulse_ms: int = 200,
    ) -> None:
        self._host     = host
        self._port     = port
        self._pulse_ms = pulse_ms
        self._running  = False
        self._lock     = threading.Lock()

        self._setup_gpio()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Binding to all interfaces is intentional: the Pi rover server must
        # accept UDP commands from the PC on whatever network interface the
        # local competition Wi-Fi is attached to.  Deploy on a trusted LAN only.
        self._sock.bind((self._host, self._port))
        self._sock.settimeout(1.0)

    # ------------------------------------------------------------------
    def _setup_gpio(self) -> None:
        if not _GPIO_AVAILABLE:
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in ALL_PINS:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    def _all_low(self) -> None:
        if not _GPIO_AVAILABLE:
            return
        for pin in ALL_PINS:
            GPIO.output(pin, GPIO.LOW)

    def _pulse(self, pin: int) -> None:
        """Activate *pin* for ``pulse_ms`` ms, then release."""
        if not _GPIO_AVAILABLE:
            return
        with self._lock:
            self._all_low()
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(self._pulse_ms / 1000.0)
            GPIO.output(pin, GPIO.LOW)

    # ------------------------------------------------------------------
    def handle_command(self, raw: str) -> None:
        """
        Dispatch a single decoded command string.

        Parameters
        ----------
        raw : str
            Command name as received over UDP (e.g. ``"FORWARD"``).
        """
        cmd = raw.strip().upper()
        if cmd == "STOP":
            self._all_low()
            return
        pin = COMMAND_PIN_MAP.get(cmd)
        if pin is not None:
            # Run the GPIO pulse in a background thread so the UDP receive
            # loop is not blocked during the pulse duration.
            threading.Thread(target=self._pulse, args=(pin,), daemon=True).start()
        else:
            print(f"[WARN] Unknown command: {cmd!r}")

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the blocking receive loop."""
        print(f"[SERVER] Listening on {self._host}:{self._port} …")
        self._running = True
        try:
            while self._running:
                try:
                    data, addr = self._sock.recvfrom(64)
                    raw = data.decode("ascii", errors="ignore")
                    print(f"[CMD] {raw.strip()!r} from {addr}")
                    self.handle_command(raw)
                except socket.timeout:
                    continue
        finally:
            self._all_low()
            if _GPIO_AVAILABLE:
                GPIO.cleanup()
            self._sock.close()
            print("[SERVER] Stopped.")

    def stop(self) -> None:
        """Signal the receive loop to terminate."""
        self._running = False


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DroneBot 2026 – Rover GPIO server")
    parser.add_argument("--host",     default="0.0.0.0", help="Bind address")
    parser.add_argument("--port",     default=5005, type=int, help="UDP port")
    parser.add_argument("--pulse-ms", default=200,  type=int, help="GPIO pulse duration (ms)")
    args = parser.parse_args()

    server = RoverServer(host=args.host, port=args.port, pulse_ms=args.pulse_ms)
    server.run()
