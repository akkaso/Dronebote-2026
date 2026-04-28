"""Test per il controllore PID."""

import sys
from pathlib import Path

# Assicura che la radice del progetto sia in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from pc.pid import PIDController


class TestPIDBasic:
    def test_solo_proporzionale(self):
        """Con ki=kd=0, l'uscita deve essere == kp * errore."""
        pid = PIDController(kp=2.0, ki=0.0, kd=0.0)
        out = pid.update(10.0, dt=0.1)
        assert out == pytest.approx(20.0)

    def test_errore_zero(self):
        pid = PIDController(kp=1.0, ki=1.0, kd=1.0)
        out = pid.update(0.0, dt=0.1)
        assert out == pytest.approx(0.0)

    def test_accumulo_integrale(self):
        """L'integrale deve accumularsi su più passi."""
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
        pid.update(1.0, dt=0.1)  # integrale = 0.1
        out = pid.update(1.0, dt=0.1)  # integrale = 0.2
        assert out == pytest.approx(0.2)

    def test_termine_derivativo(self):
        """Il derivativo reagisce alla variazione dell'errore."""
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0)
        pid.update(0.0, dt=0.1)    # errore_prec = 0
        out = pid.update(10.0, dt=0.1)  # d = 10/0.1 = 100
        assert out == pytest.approx(100.0)

    def test_reset_azzera_stato(self):
        pid = PIDController(kp=0.0, ki=1.0, kd=1.0)
        pid.update(5.0, dt=1.0)
        pid.reset()
        out = pid.update(0.0, dt=1.0)
        assert out == pytest.approx(0.0)

    def test_limite_uscita(self):
        pid = PIDController(kp=10.0, output_limit=5.0)
        out = pid.update(100.0, dt=0.1)
        assert out == pytest.approx(5.0)

    def test_limite_uscita_negativo(self):
        pid = PIDController(kp=10.0, output_limit=5.0)
        out = pid.update(-100.0, dt=0.1)
        assert out == pytest.approx(-5.0)

    def test_anti_windup(self):
        """L'integrale deve essere limitato a windup_limit."""
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0, windup_limit=10.0)
        # Alimenta un errore grande per molti passi
        for _ in range(1000):
            pid.update(100.0, dt=0.1)
        out = pid.update(0.0, dt=0.1)
        # uscita = ki * integrale_limitato = 1.0 * 10.0
        assert abs(out) <= 10.0 + 1e-9

    def test_dt_zero_non_crasha(self):
        pid = PIDController(kp=1.0)
        out = pid.update(5.0, dt=0.0)  # non deve sollevare ZeroDivisionError
        assert isinstance(out, float)

    def test_errore_negativo(self):
        pid = PIDController(kp=1.0)
        out = pid.update(-7.5, dt=0.1)
        assert out == pytest.approx(-7.5)

