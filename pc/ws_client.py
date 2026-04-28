"""
Client WebSocket robusto per DroneBot 2026 (lato PC).

Funzionalità
------------
- Invia comandi JSON con un ``msg_id`` univoco.
- Attende l'ACK dal server Pi; riprova in caso di timeout.
- Ping heartbeat periodico per rilevare connessioni interrotte.
- Modalità mock (nessuna rete) per test senza hardware.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from pc.utils import get_logger

logger = get_logger(__name__)

# Tempo di attesa per un ACK prima di riprovare (secondi)
TIMEOUT_ACK = 3.0
# Numero massimo di tentativi di invio per comando
MAX_TENTATIVI = 3
# Intervallo heartbeat (secondi)
INTERVALLO_HEARTBEAT = 5.0


class MockWSClient:
    """Client finto che registra i comandi invece di inviarli."""

    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict] = []

    async def send_command(self, payload: dict) -> bool:
        """Registra il comando e restituisce successo."""
        msg_id = payload.get("msg_id", str(uuid.uuid4())[:8])
        payload.setdefault("msg_id", msg_id)
        self.sent.append(payload)
        logger.info("[MOCK] send_command: %s", payload)
        return True

    async def close(self) -> None:
        self.connected = False


class WSClient:
    """
    Client WebSocket che si connette al server Pi.

    Utilizzo
    --------
    async with WSClient("ws://pi-host:8765") as client:
        await client.send_command({"cmd": "forward", "duration": 0.5})
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self._ws = None
        self._task_heartbeat: asyncio.Task | None = None
        self.connected = False

    async def connect(self) -> None:
        """Apre la connessione WebSocket e avvia l'heartbeat."""
        import websockets  # importato qui così la modalità mock funziona senza websockets

        self._ws = await websockets.connect(self.url)
        self.connected = True
        logger.info("Connesso a %s", self.url)
        self._task_heartbeat = asyncio.create_task(self._heartbeat())

    async def close(self) -> None:
        """Chiude la connessione in modo pulito."""
        if self._task_heartbeat:
            self._task_heartbeat.cancel()
        if self._ws:
            await self._ws.close()
        self.connected = False
        logger.info("WebSocket chiuso.")

    async def __aenter__(self) -> "WSClient":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _heartbeat(self) -> None:
        """Invia ping periodici per mantenere attiva la connessione."""
        while True:
            await asyncio.sleep(INTERVALLO_HEARTBEAT)
            try:
                await self._ws.ping()
                logger.debug("Ping heartbeat inviato.")
            except Exception as exc:
                logger.warning("Heartbeat fallito: %s", exc)
                break

    async def send_command(self, payload: dict) -> bool:
        """
        Invia un dict di comando e attende l'ACK.

        Riprova fino a MAX_TENTATIVI volte se non si riceve ACK.

        Restituisce True in caso di successo, False in caso di fallimento.
        """
        if not self.connected or self._ws is None:
            logger.error("Non connesso; impossibile inviare il comando.")
            return False

        payload = dict(payload)
        payload.setdefault("msg_id", str(uuid.uuid4()))

        for tentativo in range(1, MAX_TENTATIVI + 1):
            try:
                await self._ws.send(json.dumps(payload))
                logger.debug("Inviato (tentativo %d): %s", tentativo, payload)

                # Attendi ACK
                try:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=TIMEOUT_ACK)
                    ack = json.loads(raw)
                    if ack.get("msg_id") == payload["msg_id"]:
                        stato = ack.get("status", "ok")
                        logger.info("ACK ricevuto: %s (stato=%s)", payload["msg_id"], stato)
                        return stato != "rejected"
                    # msg_id errato — ignora e riprova
                    logger.warning("msg_id ACK non corrispondente; riprovo.")
                except asyncio.TimeoutError:
                    logger.warning("Timeout ACK (tentativo %d/%d)", tentativo, MAX_TENTATIVI)
            except Exception as exc:
                logger.error("Errore di invio: %s", exc)
                return False

        logger.error("Impossibile ricevere ACK dopo %d tentativi.", MAX_TENTATIVI)
        return False

