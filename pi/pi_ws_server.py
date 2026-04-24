"""
DroneBot 2026 – Pi WebSocket server.

Accepts JSON commands from the PC client:
    { "cmd": "forward"|"left"|"right"|"back"|"stop", "duration": float, "msg_id": str }

Special commands:
    { "cmd": "emergency_stop" }  – stops all motors, enters ESTOP state (ignores
                                    further movement until restart)
    { "cmd": "heartbeat" }       – replies with pong (no GPIO action)

Sends ACK:
    { "msg_id": str, "status": "ok" | "rejected" }

Usage
-----
python3 pi_ws_server.py [--host HOST] [--port PORT] [--mock]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import websockets
from websockets.server import WebSocketServerProtocol

sys.path.insert(0, str(Path(__file__).parent.parent))
from pi.gpio_controller import get_controller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pi_ws_server")

# Movement commands that the GPIO controller handles
MOVEMENT_COMMANDS = {"forward", "left", "right", "back", "stop"}

# Global emergency-stop flag (set on emergency_stop command)
_ESTOP = False
_gpio = None  # initialised in main()


async def handle_client(ws: WebSocketServerProtocol) -> None:
    """Handle a single connected PC client."""
    global _ESTOP

    client_addr = ws.remote_address
    logger.info("Client connected: %s", client_addr)

    try:
        async for raw in ws:
            # ── Parse JSON ───────────────────────────────────────────
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from %s: %r", client_addr, raw)
                continue

            cmd = msg.get("cmd", "")
            msg_id = msg.get("msg_id", "")
            duration = float(msg.get("duration", 0.0))

            logger.info("Received cmd=%r msg_id=%r duration=%.3f", cmd, msg_id, duration)

            # ── Emergency stop ───────────────────────────────────────
            if cmd == "emergency_stop":
                logger.warning("EMERGENCY STOP received!")
                _gpio.stop_all()
                _ESTOP = True
                await _send_ack(ws, msg_id, "ok")
                continue

            # ── Heartbeat ────────────────────────────────────────────
            if cmd == "heartbeat":
                await _send_ack(ws, msg_id, "ok")
                continue

            # ── ESTOP active – reject movement ───────────────────────
            if _ESTOP:
                logger.warning("ESTOP active – rejecting cmd=%r", cmd)
                await _send_ack(ws, msg_id, "rejected")
                continue

            # ── Movement commands ────────────────────────────────────
            if cmd in MOVEMENT_COMMANDS:
                # Run GPIO in a thread so we don't block the event loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, _gpio.press_button, cmd, duration
                )
                await _send_ack(ws, msg_id, "ok")
            else:
                logger.warning("Unknown command: %r", cmd)
                await _send_ack(ws, msg_id, "rejected")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Client %s disconnected cleanly.", client_addr)
    except websockets.exceptions.ConnectionClosedError as exc:
        logger.warning("Client %s connection error: %s", client_addr, exc)
    finally:
        logger.info("Handler for %s finished.", client_addr)


async def _send_ack(ws: WebSocketServerProtocol, msg_id: str, status: str) -> None:
    """Send a JSON ACK message."""
    try:
        await ws.send(json.dumps({"msg_id": msg_id, "status": status}))
    except Exception as exc:
        logger.error("Failed to send ACK: %s", exc)


async def serve(host: str, port: int) -> None:
    logger.info("Starting WebSocket server on %s:%d (ESTOP=%s)", host, port, _ESTOP)
    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()  # run forever


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DroneBot 2026 Pi WebSocket server")
    p.add_argument("--host", default="0.0.0.0", help="Bind host")
    p.add_argument("--port", type=int, default=8765, help="Bind port")
    p.add_argument("--mock", action="store_true", help="Use MockGPIO (no hardware needed)")
    return p.parse_args()


def main() -> None:
    global _gpio
    args = parse_args()
    _gpio = get_controller(mock=args.mock)
    logger.info("GPIO controller: %s", type(_gpio).__name__)
    asyncio.run(serve(args.host, args.port))


if __name__ == "__main__":
    main()
