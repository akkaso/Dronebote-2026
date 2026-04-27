"""
Controllore GPIO per DroneBot 2026 (lato Pi).

Fornisce
--------
- ``RealGPIO``  – usa RPi.GPIO (funziona solo su Raspberry Pi)
- ``MockGPIO``  – stub thread-safe per test senza hardware
- ``get_controller(mock=False)`` – funzione factory

Entrambe le classi espongono:
    premi_pulsante(pulsante: str, durata: float) -> None
    ferma_tutto() -> None
"""

from __future__ import annotations

import threading
import time
import logging

logger = logging.getLogger(__name__)

# ── Mappa pulsante → pin GPIO BCM ────────────────────────────────────
BUTTON_PINS: dict[str, int] = {
    "forward": 17,  # avanti
    "left":    27,  # sinistra
    "right":   22,  # destra
    "back":    10,  # indietro
    "stop":     9,  # stop (pulsante dedicato opzionale)
}

# Tempo massimo (secondi) per cui un singolo pulsante può essere tenuto premuto
MAX_PRESS_TIMEOUT: float = 5.0


class MockGPIO:
    """
    Controllore GPIO mock thread-safe per test e sviluppo.

    Registra tutte le chiamate in ``self.log`` così i test possono verificare il comportamento.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.log: list[dict] = []
        self._attivi: set[str] = set()
        logger.info("MockGPIO inizializzato.")

    def press_button(self, pulsante: str, durata: float) -> None:
        """
        Simula la pressione di *pulsante* per *durata* secondi.

        Limita *durata* a [0, MAX_PRESS_TIMEOUT].
        Thread-safe: un solo pulsante attivo alla volta.
        """
        durata = max(0.0, min(durata, MAX_PRESS_TIMEOUT))
        with self._lock:
            logger.info("[MockGPIO] press_button(%s, %.3fs)", pulsante, durata)
            self._attivi.add(pulsante)
            self.log.append({"action": "press", "button": pulsante, "duration": durata})

        time.sleep(durata)

        with self._lock:
            self._attivi.discard(pulsante)
            self.log.append({"action": "release", "button": pulsante})

    def stop_all(self) -> None:
        """Simula il rilascio immediato di tutti i pulsanti."""
        with self._lock:
            logger.info("[MockGPIO] stop_all")
            self._attivi.clear()
            self.log.append({"action": "stop_all"})


class RealGPIO:
    """
    Controllore RPi.GPIO reale.

    Richiede il pacchetto ``RPi.GPIO`` (disponibile su Raspberry Pi).
    Solleva ``ImportError`` se non è in esecuzione su hardware supportato.
    """

    def __init__(self) -> None:
        try:
            import RPi.GPIO as GPIO  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "RPi.GPIO non è disponibile. Avvia con --mock su hardware non-Pi."
            ) from exc

        self._GPIO = GPIO
        self._lock = threading.Lock()

        GPIO.setmode(GPIO.BCM)
        for pin in BUTTON_PINS.values():
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        logger.info("RealGPIO inizializzato (modalità BCM).")

    def _imposta_pin(self, pulsante: str, stato: bool) -> None:
        pin = BUTTON_PINS.get(pulsante)
        if pin is None:
            logger.warning("Pulsante sconosciuto: %s", pulsante)
            return
        self._GPIO.output(pin, self._GPIO.HIGH if stato else self._GPIO.LOW)

    def press_button(self, pulsante: str, durata: float) -> None:
        """
        Porta il pin GPIO di *pulsante* HIGH per *durata* secondi, poi lo abbassa.

        Thread-safe, durata limitata a MAX_PRESS_TIMEOUT.
        """
        durata = max(0.0, min(durata, MAX_PRESS_TIMEOUT))
        with self._lock:
            logger.info("[RealGPIO] press_button(%s, %.3fs)", pulsante, durata)
            self._imposta_pin(pulsante, True)

        time.sleep(durata)

        with self._lock:
            self._imposta_pin(pulsante, False)

    def stop_all(self) -> None:
        """Porta immediatamente tutti i pin GPIO a LOW."""
        with self._lock:
            logger.info("[RealGPIO] stop_all")
            for pulsante in BUTTON_PINS:
                self._imposta_pin(pulsante, False)

    def cleanup(self) -> None:
        """Rilascia le risorse GPIO (chiamare alla chiusura)."""
        self.stop_all()
        self._GPIO.cleanup()


def get_controller(mock: bool = False) -> MockGPIO | RealGPIO:
    """Restituisce MockGPIO o RealGPIO in base al flag *mock*."""
    if mock:
        return MockGPIO()
    return RealGPIO()

