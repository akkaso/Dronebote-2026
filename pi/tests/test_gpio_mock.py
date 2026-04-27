"""Test per il controllore MockGPIO."""

import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from pi.gpio_controller import MockGPIO, MAX_PRESS_TIMEOUT


class TestMockGPIO:
    def setup_method(self):
        self.gpio = MockGPIO()

    def test_press_button_registra_pressione_e_rilascio(self):
        self.gpio.press_button("forward", 0.01)
        azioni = [e["action"] for e in self.gpio.log]
        assert "press" in azioni
        assert "release" in azioni

    def test_press_button_nome_corretto(self):
        self.gpio.press_button("left", 0.01)
        eventi_press = [e for e in self.gpio.log if e["action"] == "press"]
        assert eventi_press[0]["button"] == "left"

    def test_durata_pressione_limitata_al_massimo(self):
        self.gpio.press_button("forward", MAX_PRESS_TIMEOUT + 100)
        eventi_press = [e for e in self.gpio.log if e["action"] == "press"]
        assert eventi_press[0]["duration"] <= MAX_PRESS_TIMEOUT

    def test_durata_pressione_limitata_a_zero(self):
        self.gpio.press_button("forward", -1.0)
        eventi_press = [e for e in self.gpio.log if e["action"] == "press"]
        assert eventi_press[0]["duration"] == 0.0

    def test_stop_all_registra_evento(self):
        self.gpio.stop_all()
        azioni = [e["action"] for e in self.gpio.log]
        assert "stop_all" in azioni

    def test_pulsanti_multipli(self):
        for btn in ["forward", "left", "right", "back"]:
            self.gpio.press_button(btn, 0.0)
        pulsanti_premuti = [e["button"] for e in self.gpio.log if e["action"] == "press"]
        assert set(pulsanti_premuti) == {"forward", "left", "right", "back"}

    def test_sicurezza_thread(self):
        """Più thread che premono pulsanti contemporaneamente non devono crashare."""
        def premi(btn):
            self.gpio.press_button(btn, 0.01)

        thread_list = [threading.Thread(target=premi, args=(b,))
                       for b in ["forward", "left", "right"]]
        for t in thread_list:
            t.start()
        for t in thread_list:
            t.join()

        contatore_press = sum(1 for e in self.gpio.log if e["action"] == "press")
        assert contatore_press == 3

    def test_stop_all_svuota_attivi(self):
        """stop_all deve svuotare l'insieme degli attivi."""
        self.gpio._attivi.add("forward")
        self.gpio.stop_all()
        assert len(self.gpio._attivi) == 0

