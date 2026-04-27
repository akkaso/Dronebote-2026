"""Controllore PID con anti-windup per DroneBot 2026."""

from pc.utils import clamp


class PIDController:
    """
    Controllore PID discreto.

    Parametri
    ---------
    kp, ki, kd : float
        Guadagni proporzionale, integrale, derivativo.
    windup_limit : float
        Valore assoluto massimo dell'accumulatore integrale (anti-windup).
    output_limit : float oppure None
        Se impostato, limita l'uscita finale a [-output_limit, output_limit].
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        windup_limit: float = 100.0,
        output_limit: float | None = None,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.windup_limit = windup_limit
        self.output_limit = output_limit

        self._integrale: float = 0.0
        self._errore_prec: float = 0.0

    def reset(self) -> None:
        """Azzera lo stato interno (chiamare quando si cambia bersaglio)."""
        self._integrale = 0.0
        self._errore_prec = 0.0

    def update(self, error: float, dt: float) -> float:
        """
        Calcola l'uscita PID per *error* nel passo temporale *dt* (secondi).

        Restituisce il segnale di controllo (positivo → gira a destra,
        negativo → gira a sinistra nella convenzione di navigazione del progetto).
        """
        if dt <= 0:
            dt = 1e-6  # evita divisione per zero

        # Termine proporzionale
        p = self.kp * error

        # Termine integrale con saturazione anti-windup
        self._integrale += error * dt
        self._integrale = clamp(self._integrale, -self.windup_limit, self.windup_limit)
        i = self.ki * self._integrale

        # Termine derivativo (differenza all'indietro)
        d = self.kd * (error - self._errore_prec) / dt
        self._errore_prec = error

        uscita = p + i + d
        if self.output_limit is not None:
            uscita = clamp(uscita, -self.output_limit, self.output_limit)
        return uscita

