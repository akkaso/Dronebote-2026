"""Funzioni di supporto condivise per il lato PC."""

import logging
import time


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Restituisce un logger configurato."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def clamp(value: float, low: float, high: float) -> float:
    """Limita *value* all'intervallo [low, high]."""
    return max(low, min(high, value))


class FPSTimer:
    """Helper semplice per misurare i fotogrammi al secondo."""

    def __init__(self) -> None:
        self._ultimo = time.monotonic()
        self.fps = 0.0

    def tick(self) -> float:
        """Chiamare una volta per frame; restituisce il dt corrente in secondi."""
        ora = time.monotonic()
        dt = ora - self._ultimo
        self._ultimo = ora
        self.fps = 1.0 / dt if dt > 0 else 0.0
        return dt

