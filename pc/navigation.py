"""Conversione dell'output PID in comandi discreti per DroneBot 2026."""

from __future__ import annotations

from pc.pid import PIDController
from pc.utils import get_logger

logger = get_logger(__name__)

# Costanti per i comandi discreti
CMD_AVANTI   = "forward"
CMD_SINISTRA = "left"
CMD_DESTRA   = "right"
CMD_STOP     = "stop"

# Soglie predefinite (errore laterale in pixel)
SOGLIA_SVOLTA_DEFAULT = 40    # sotto questa soglia → vai dritto
DURATA_BASE_DEFAULT   = 0.3   # secondi per comando

# Output PID massimo mappato a questa durata massima (secondi)
DURATA_MASSIMA = 1.5


def decide_command(
    pid_output: float,
    fire_detected: bool,
    pid: PIDController | None = None,
    turn_threshold: float = SOGLIA_SVOLTA_DEFAULT,
    base_duration: float = DURATA_BASE_DEFAULT,
) -> dict:
    """
    Converte *pid_output* (segnale di correzione laterale) in un dict di comando.

    Parametri
    ---------
    pid_output      : float — uscita grezza del PID (positivo → fuoco a destra del centro)
    fire_detected   : bool  — se il fuoco è stato trovato nel frame
    pid             : non utilizzato, mantenuto per compatibilità API
    turn_threshold  : float — |pid_output| sotto questa soglia → vai avanti
    base_duration   : float — durata minima del comando in secondi

    Restituisce
    -----------
    dict con chiavi ``cmd`` (str) e ``duration`` (float, secondi)
    """
    if not fire_detected:
        return {"cmd": CMD_STOP, "duration": 0.0}

    valore_assoluto = abs(pid_output)

    # Durata proporzionale alla correzione necessaria
    duration = base_duration + min(valore_assoluto / 200.0, DURATA_MASSIMA - base_duration)

    if valore_assoluto < turn_threshold:
        cmd = CMD_AVANTI
    elif pid_output > 0:
        cmd = CMD_DESTRA
    else:
        cmd = CMD_SINISTRA

    logger.debug("decide_command: pid_out=%.2f → %s %.2fs", pid_output, cmd, duration)
    return {"cmd": cmd, "duration": round(duration, 3)}

