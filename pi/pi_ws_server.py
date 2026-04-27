"""
DroneBot 2026 – Server WebSocket Pi.

Accetta comandi JSON dal client PC:
    { "cmd": "forward"|"left"|"right"|"back"|"stop", "duration": float, "msg_id": str }

Comandi speciali:
    { "cmd": "emergency_stop" }  – ferma tutti i motori, entra in stato ESTOP (ignora
                                    ulteriori movimenti fino al riavvio)
    { "cmd": "heartbeat" }       – risponde con pong (nessuna azione GPIO)

Invia ACK:
    { "msg_id": str, "status": "ok" | "rejected" }

Utilizzo
--------
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

# Comandi di movimento gestiti dal controllore GPIO
COMANDI_MOVIMENTO = {"forward", "left", "right", "back", "stop"}

# Flag di arresto di emergenza globale (impostato dal comando emergency_stop)
_ESTOP = False
_gpio = None  # inizializzato in main()


async def gestisci_client(ws: WebSocketServerProtocol) -> None:
    """Gestisce un singolo client PC connesso."""
    global _ESTOP

    indirizzo_client = ws.remote_address
    logger.info("Client connesso: %s", indirizzo_client)

    try:
        async for raw in ws:
            # ── Analisi JSON ──────────────────────────────────────────
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("JSON non valido da %s: %r", indirizzo_client, raw)
                continue

            cmd = msg.get("cmd", "")
            msg_id = msg.get("msg_id", "")
            durata = float(msg.get("duration", 0.0))

            logger.info("Ricevuto cmd=%r msg_id=%r durata=%.3f", cmd, msg_id, durata)

            # ── Arresto di emergenza ──────────────────────────────────
            if cmd == "emergency_stop":
                logger.warning("ARRESTO DI EMERGENZA ricevuto!")
                _gpio.stop_all()
                _ESTOP = True
                await _invia_ack(ws, msg_id, "ok")
                continue

            # ── Heartbeat ─────────────────────────────────────────────
            if cmd == "heartbeat":
                await _invia_ack(ws, msg_id, "ok")
                continue

            # ── ESTOP attivo – rifiuta il movimento ───────────────────
            if _ESTOP:
                logger.warning("ESTOP attivo – rifiuto cmd=%r", cmd)
                await _invia_ack(ws, msg_id, "rejected")
                continue

            # ── Comandi di movimento ──────────────────────────────────
            if cmd in COMANDI_MOVIMENTO:
                # Esegui GPIO in un thread separato per non bloccare l'event loop
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, _gpio.press_button, cmd, durata
                )
                await _invia_ack(ws, msg_id, "ok")
            else:
                logger.warning("Comando sconosciuto: %r", cmd)
                await _invia_ack(ws, msg_id, "rejected")

    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Client %s disconnesso in modo pulito.", indirizzo_client)
    except websockets.exceptions.ConnectionClosedError as exc:
        logger.warning("Errore connessione client %s: %s", indirizzo_client, exc)
    finally:
        logger.info("Handler per %s terminato.", indirizzo_client)


async def _invia_ack(ws: WebSocketServerProtocol, msg_id: str, stato: str) -> None:
    """Invia un messaggio ACK JSON."""
    try:
        await ws.send(json.dumps({"msg_id": msg_id, "status": stato}))
    except Exception as exc:
        logger.error("Impossibile inviare ACK: %s", exc)


async def avvia_server(host: str, port: int) -> None:
    logger.info("Avvio server WebSocket su %s:%d (ESTOP=%s)", host, port, _ESTOP)
    async with websockets.serve(gestisci_client, host, port):
        await asyncio.Future()  # esegui per sempre


def analizza_argomenti() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DroneBot 2026 – Server WebSocket Pi")
    p.add_argument("--host", default="0.0.0.0", help="Host di ascolto")
    p.add_argument("--port", type=int, default=8765, help="Porta di ascolto")
    p.add_argument("--mock", action="store_true", help="Usa MockGPIO (nessun hardware necessario)")
    return p.parse_args()


def main() -> None:
    global _gpio
    args = analizza_argomenti()
    _gpio = get_controller(mock=args.mock)
    logger.info("Controllore GPIO: %s", type(_gpio).__name__)
    asyncio.run(avvia_server(args.host, args.port))


if __name__ == "__main__":
    main()

