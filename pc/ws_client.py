"""
Robust WebSocket client for DroneBot 2026 (PC side).

Features
--------
- Sends JSON commands with a unique ``msg_id``.
- Waits for ACK from the Pi server; retries on timeout.
- Periodic heartbeat ping to detect dead connections.
- Mock mode (no network needed) for testing without hardware.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from pc.utils import get_logger

logger = get_logger(__name__)

# How long to wait for an ACK before retrying (seconds)
ACK_TIMEOUT = 3.0
# Max number of send retries per command
MAX_RETRIES = 3
# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 5.0


class MockWSClient:
    """Fake client that logs commands instead of sending them."""

    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict] = []

    async def send_command(self, payload: dict) -> bool:
        """Log the command and return success."""
        msg_id = payload.get("msg_id", str(uuid.uuid4())[:8])
        payload.setdefault("msg_id", msg_id)
        self.sent.append(payload)
        logger.info("[MOCK] send_command: %s", payload)
        return True

    async def close(self) -> None:
        self.connected = False


class WSClient:
    """
    WebSocket client that connects to the Pi server.

    Usage
    -----
    async with WSClient("ws://pi-host:8765") as client:
        await client.send_command({"cmd": "forward", "duration": 0.5})
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._ws = None
        self._heartbeat_task: asyncio.Task | None = None
        self.connected = False

    async def connect(self) -> None:
        """Open the WebSocket connection and start the heartbeat."""
        import websockets  # imported here so mock mode works without websockets

        self._ws = await websockets.connect(self.url)
        self.connected = True
        logger.info("Connected to %s", self.url)
        self._heartbeat_task = asyncio.create_task(self._heartbeat())

    async def close(self) -> None:
        """Cleanly close the connection."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._ws:
            await self._ws.close()
        self.connected = False
        logger.info("WebSocket closed.")

    async def __aenter__(self) -> "WSClient":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _heartbeat(self) -> None:
        """Send periodic pings to keep the connection alive."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await self._ws.ping()
                logger.debug("Heartbeat ping sent.")
            except Exception as exc:
                logger.warning("Heartbeat failed: %s", exc)
                break

    async def send_command(self, payload: dict) -> bool:
        """
        Send a command dict and wait for ACK.

        Retries up to MAX_RETRIES times if no ACK is received.

        Returns True on success, False on failure.
        """
        if not self.connected or self._ws is None:
            logger.error("Not connected; cannot send command.")
            return False

        payload = dict(payload)
        payload.setdefault("msg_id", str(uuid.uuid4()))

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self._ws.send(json.dumps(payload))
                logger.debug("Sent (attempt %d): %s", attempt, payload)

                # Wait for ACK
                try:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=ACK_TIMEOUT)
                    ack = json.loads(raw)
                    if ack.get("msg_id") == payload["msg_id"]:
                        status = ack.get("status", "ok")
                        logger.info("ACK received: %s (status=%s)", payload["msg_id"], status)
                        return status != "rejected"
                    # Wrong msg_id — ignore and retry
                    logger.warning("ACK msg_id mismatch; retrying.")
                except asyncio.TimeoutError:
                    logger.warning("ACK timeout (attempt %d/%d)", attempt, MAX_RETRIES)
            except Exception as exc:
                logger.error("Send error: %s", exc)
                return False

        logger.error("Failed to get ACK after %d attempts.", MAX_RETRIES)
        return False
