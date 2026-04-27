"""
DroneBot 2026 – Client di visione PC (punto di ingresso principale).

Utilizzo
--------
python3 vision_client.py [OPZIONI]

Opzioni
-------
--source SOURCE     Sorgente video: URL RTSP, URL HTTP, percorso file, o int (indice telecamera).
                    Riserva: sample_video.mp4 poi pc/sample_frames/.
--ws WS_URL         URL WebSocket del server Pi (default: ws://localhost:8765).
--mock              Usa MockWSClient (nessuna connessione WebSocket).
--no-display        Disabilita la finestra OpenCV imshow.
--debug             Salva i frame annotati in pc/debug/.
--config CONFIG     Percorso di config.yaml (default: pc/config.yaml).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

# Permette l'esecuzione come `python3 pc/vision_client.py` dalla radice del progetto
sys.path.insert(0, str(Path(__file__).parent.parent))

from pc.aruco_detector import ArucoDetector
from pc.navigation import decide_command
from pc.pid import PIDController
from pc.utils import FPSTimer, get_logger
from pc.ws_client import MockWSClient, WSClient

logger = get_logger("vision_client")

# ──────────────────────────────────────────────────────
# Valori predefiniti (sovrascritti da config.yaml)
# ──────────────────────────────────────────────────────
PREDEFINITI = {
    "fire_hsv_lower": [0, 120, 120],
    "fire_hsv_upper": [30, 255, 255],
    "min_contour_area": 500,
    "pid_kp": 0.8,
    "pid_ki": 0.05,
    "pid_kd": 0.1,
    "pid_windup_limit": 300.0,
    "pid_output_limit": 500.0,
    "turn_threshold": 40,
    "base_duration": 0.3,
    "ws_url": "ws://localhost:8765",
    "camera_index": 0,
    "debug_save": True,
    "display": True,
}

DIR_CORRENTE = Path(__file__).parent
VIDEO_ESEMPIO = Path(__file__).parent.parent / "sample_video.mp4"
DIR_FRAME_ESEMPIO = DIR_CORRENTE / "sample_frames"
DIR_DEBUG = DIR_CORRENTE / "debug"


def carica_config(percorso: str) -> dict:
    cfg = dict(PREDEFINITI)
    try:
        with open(percorso) as f:
            caricato = yaml.safe_load(f) or {}
        cfg.update(caricato)
    except FileNotFoundError:
        logger.warning("Config non trovato in %s; uso i valori predefiniti.", percorso)
    return cfg


# ──────────────────────────────────────────────────────
# Helper per la sorgente video
# ──────────────────────────────────────────────────────

def apri_video(sorgente: str | int) -> cv2.VideoCapture | None:
    """Prova ad aprire *sorgente*; restituisce la cattura o None."""
    cap = cv2.VideoCapture(sorgente)
    if cap.isOpened():
        return cap
    cap.release()
    return None


def cattura_riserva() -> cv2.VideoCapture | None:
    """Prova sample_video.mp4, poi itera su sample_frames/."""
    if VIDEO_ESEMPIO.exists() and VIDEO_ESEMPIO.stat().st_size > 0:
        logger.info("Riserva: uso %s", VIDEO_ESEMPIO)
        return apri_video(str(VIDEO_ESEMPIO))
    logger.warning("sample_video.mp4 non trovato o vuoto; uso sample_frames/")
    return None  # il chiamante userà la modalità frame statici


def carica_frame_esempio() -> list[np.ndarray]:
    """Carica tutti i file immagine da sample_frames/ ordinati per nome."""
    frames = []
    for p in sorted(DIR_FRAME_ESEMPIO.glob("*.jpg")) + sorted(DIR_FRAME_ESEMPIO.glob("*.png")):
        img = cv2.imread(str(p))
        if img is not None:
            frames.append(img)
    return frames


# ──────────────────────────────────────────────────────
# Rilevamento fuoco
# ──────────────────────────────────────────────────────

def rileva_fuoco(
    frame: np.ndarray,
    hsv_min: list,
    hsv_max: list,
    area_min: int,
) -> tuple[bool, tuple[int, int] | None, np.ndarray]:
    """
    Rileva colori simili al fuoco in *frame* tramite sogliatura HSV + morfologia.

    Restituisce
    -----------
    rilevato   : bool
    centroide  : coordinate pixel (cx, cy) del blob più grande, o None
    maschera   : maschera binaria (per il display di debug)
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    minimo = np.array(hsv_min, dtype=np.uint8)
    massimo = np.array(hsv_max, dtype=np.uint8)
    maschera = cv2.inRange(hsv, minimo, massimo)

    # Pulizia morfologica
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    maschera = cv2.morphologyEx(maschera, cv2.MORPH_OPEN, kernel)
    maschera = cv2.morphologyEx(maschera, cv2.MORPH_DILATE, kernel)

    contorni, _ = cv2.findContours(maschera, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contorni:
        return False, None, maschera

    piu_grande = max(contorni, key=cv2.contourArea)
    if cv2.contourArea(piu_grande) < area_min:
        return False, None, maschera

    M = cv2.moments(piu_grande)
    if M["m00"] == 0:
        return False, None, maschera

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return True, (cx, cy), maschera


# ──────────────────────────────────────────────────────
# Overlay frame di debug
# ──────────────────────────────────────────────────────

def annota_frame(
    frame: np.ndarray,
    fuoco_rilevato: bool,
    centroide: tuple[int, int] | None,
    comando: dict,
    fps: float,
    maschera: np.ndarray | None = None,
) -> np.ndarray:
    out = frame.copy()
    h, w = out.shape[:2]

    # Centroide del fuoco
    if fuoco_rilevato and centroide:
        cv2.circle(out, centroide, 15, (0, 0, 255), 3)
        cv2.line(out, (w // 2, 0), (w // 2, h), (255, 255, 0), 1)

    # Overlay comando
    etichetta = f"CMD: {comando.get('cmd','?')} ({comando.get('duration',0):.2f}s)"
    cv2.putText(out, etichetta, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(out, f"FPS: {fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 2)

    if not fuoco_rilevato:
        cv2.putText(out, "NESSUN FUOCO", (w // 2 - 80, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)
    return out


def salva_frame_debug(frame: np.ndarray, indice: int) -> None:
    DIR_DEBUG.mkdir(parents=True, exist_ok=True)
    percorso = DIR_DEBUG / f"frame_{indice:06d}.jpg"
    cv2.imwrite(str(percorso), frame)


# ──────────────────────────────────────────────────────
# Loop asincrono principale
# ──────────────────────────────────────────────────────

async def run(args: argparse.Namespace, cfg: dict) -> None:
    # Costruisce il client WS
    if args.mock:
        ws = MockWSClient()
    else:
        ws = WSClient(args.ws or cfg["ws_url"])
        await ws.connect()

    # PID
    pid = PIDController(
        kp=cfg["pid_kp"],
        ki=cfg["pid_ki"],
        kd=cfg["pid_kd"],
        windup_limit=cfg["pid_windup_limit"],
        output_limit=cfg["pid_output_limit"],
    )

    # Rilevatore ArUco (senza matrice telecamera → nessuna stima posa in modalità default)
    aruco = ArucoDetector()

    # Apre la sorgente video
    cap = None
    frame_statici: list[np.ndarray] = []
    idx_statico = 0

    if args.source:
        # Prima prova come int (indice telecamera)
        try:
            src: str | int = int(args.source)
        except (ValueError, TypeError):
            src = args.source
        cap = apri_video(src)
    else:
        # Riserva: usa camera_index dalla configurazione
        idx_cam = cfg.get("camera_index", 0)
        cap = apri_video(idx_cam)

    if cap is None:
        cap = cattura_riserva()

    if cap is None:
        frame_statici = carica_frame_esempio()
        if not frame_statici:
            logger.error("Nessuna sorgente video disponibile e nessun frame di esempio trovato. Uscita.")
            await ws.close()
            return
        logger.info("Uso %d frame di esempio statici (loop).", len(frame_statici))

    timer = FPSTimer()
    indice_frame = 0
    mostra = cfg.get("display", True) and not args.no_display
    salva_debug = cfg.get("debug_save", True) or args.debug

    logger.info("Avvio loop di visione. Premi 'q' per uscire.")

    try:
        while True:
            # Leggi frame
            if cap is not None:
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # riavvolgi
                    ok, frame = cap.read()
                if not ok:
                    logger.warning("Impossibile leggere il frame; interruzione.")
                    break
            else:
                frame = frame_statici[idx_statico % len(frame_statici)]
                idx_statico += 1
                await asyncio.sleep(0.033)  # ~30 fps

            dt = timer.tick()
            h, w = frame.shape[:2]
            centro_frame_x = w // 2

            # Rilevamento fuoco
            fuoco_rilevato, centroide, maschera = rileva_fuoco(
                frame,
                cfg["fire_hsv_lower"],
                cfg["fire_hsv_upper"],
                cfg["min_contour_area"],
            )

            # Errore laterale: positivo → fuoco a destra del centro
            if fuoco_rilevato and centroide:
                errore = centroide[0] - centro_frame_x
            else:
                errore = 0.0
                pid.reset()

            output_pid = pid.update(errore, dt)

            # Decidi il comando
            comando = decide_command(
                output_pid,
                fuoco_rilevato,
                turn_threshold=cfg["turn_threshold"],
                base_duration=cfg["base_duration"],
            )

            # ArUco (opzionale, per logging/uso futuro)
            corners, ids, rvecs, tvecs = aruco.detect(frame)
            if ids:
                logger.debug("ID ArUco rilevati: %s", ids)

            # Invia il comando
            await ws.send_command(comando)

            # Annota e mostra/salva
            annotato = annota_frame(frame, fuoco_rilevato, centroide, comando, timer.fps)
            if len(corners) > 0:
                annotato = aruco.draw(annotato, corners, ids)

            if mostra:
                cv2.imshow("DroneBot 2026 – Visione PC", annotato)
                tasto = cv2.waitKey(1) & 0xFF
                if tasto == ord("q"):
                    break

            if salva_debug:
                salva_frame_debug(annotato, indice_frame)

            indice_frame += 1
            await asyncio.sleep(0)  # cede il controllo all'event loop

    finally:
        if cap is not None:
            cap.release()
        if mostra:
            cv2.destroyAllWindows()
        await ws.close()


def analizza_argomenti() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DroneBot 2026 – client di visione PC")
    p.add_argument("--source", default=None, help="Sorgente video (URL, file, indice telecamera)")
    p.add_argument("--ws", default=None, help="URL WebSocket (ws://host:porta)")
    p.add_argument("--mock", action="store_true", help="Usa client WS mock")
    p.add_argument("--no-display", action="store_true", help="Disabilita la finestra OpenCV")
    p.add_argument("--debug", action="store_true", help="Salva i frame di debug")
    p.add_argument("--config", default=str(DIR_CORRENTE / "config.yaml"), help="Percorso config.yaml")
    return p.parse_args()


if __name__ == "__main__":
    args = analizza_argomenti()
    cfg = carica_config(args.config)
    asyncio.run(run(args, cfg))

