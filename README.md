# DroneBot 2026

DroneBot 2026 è un sistema robotico a guida autonoma che rileva incendi tramite visione artificiale (PC) e si avvicina alla sorgente del fuoco grazie a un Raspberry Pi che controlla i motori via GPIO. La comunicazione tra PC e Pi avviene tramite WebSocket.

## Architettura

```
[Telecamera / Sorgente Video]
        |
      [PC]  ← Rilevamento fuoco con OpenCV + stima posa ArUco
        |       ↓ WebSocket (comandi JSON)
      [Pi]  ← Controllo motori via GPIO
```

- **Lato PC**: acquisisce il video, rileva il fuoco tramite sogliatura HSV, stima la posizione con marker ArUco, invia comandi discreti (avanti/sinistra/destra/stop) con durata tramite WebSocket.
- **Lato Pi**: riceve i comandi, aziona i motori via GPIO, invia conferme (ACK), supporta arresto di emergenza.

## Avvio Rapido

### Requisiti

- Python 3.10+
- PC: `pip install -r requirements-pc.txt`
- Pi: `pip install -r requirements-pi.txt`

### Genera video di test

```bash
python3 scripts/genera_video_esempio.py
```

### Avvia la demo (client PC mock + server Pi mock)

```bash
bash scripts/esecuzione_esempio.sh
```

### Avvia il server sul Raspberry Pi

```bash
bash pi/avvia_pi.sh --host 0.0.0.0 --port 8765
```

### Avvia il client PC

```bash
bash pc/avvia_pc.sh --source sample_video.mp4 --ws ws://localhost:8765
```

Modifica `pc/config.yaml` per personalizzare i parametri.

## Docker

```bash
docker-compose up
```

## Struttura del Progetto

```
.
├── pc/                    # Visione artificiale e controllo (lato PC)
│   ├── vision_client.py   # Punto di ingresso principale (CLI)
│   ├── aruco_detector.py  # Rilevamento marker ArUco e stima posa
│   ├── pid.py             # Controllore PID con anti-windup
│   ├── navigation.py      # Conversione output PID in comandi discreti
│   ├── ws_client.py       # Client WebSocket con ack/retry/heartbeat
│   ├── utils.py           # Funzioni di supporto condivise
│   ├── config.yaml        # Parametri configurabili
│   ├── Dockerfile
│   ├── avvia_pc.sh
│   ├── sample_frames/     # Frame statici di riserva
│   ├── debug/             # Frame di debug salvati
│   └── tests/
│       ├── test_pid.py
│       └── test_aruco.py
├── pi/                    # Server GPIO Raspberry Pi
│   ├── pi_ws_server.py    # Server WebSocket
│   ├── gpio_controller.py # Controllo GPIO (reale + mock)
│   ├── Dockerfile
│   ├── avvia_pi.sh
│   ├── systemd/
│   │   └── dronbot_pi.service
│   └── tests/
│       └── test_gpio_mock.py
├── docs/
│   ├── GUIDA_INSTALLAZIONE.md  # ← Guida dettagliata PC + Raspberry Pi
│   ├── INSTALL.md
│   ├── USO.md
│   ├── PRESENTAZIONE.md
│   └── pseudocodice.txt
├── scripts/
│   ├── esecuzione_esempio.sh
│   └── genera_video_esempio.py
├── ci/
│   └── github-actions.yml
├── .github/workflows/
├── requirements-pc.txt
├── requirements-pi.txt
├── docker-compose.yml
├── diagramma_flusso.txt
└── sample_video.mp4
```

## Configurazione

Tutti i parametri modificabili si trovano in `pc/config.yaml`:

- `fire_hsv_lower` / `fire_hsv_upper`: intervallo HSV per il rilevamento del fuoco
- `min_contour_area`: area minima in pixel per considerare un blob come fuoco
- `pid_kp/ki/kd`: guadagni del PID
- `ws_url`: indirizzo del server WebSocket
- `camera_index`: indice della telecamera locale
- `debug_save`: salva i frame di debug annotati in `pc/debug/`

## Sicurezza

- **Arresto di emergenza**: inviando `{"cmd":"emergency_stop"}` al server Pi si fermano immediatamente tutti i motori e vengono ignorati ulteriori comandi di movimento fino al riavvio del processo.
- **Modalità mock**: sia il PC che il Pi supportano il flag `--mock` per testare l'intero sistema senza hardware.
- **Heartbeat**: il client PC invia ping periodici; il server Pi disconnette i client che non rispondono.

## Test

```bash
pytest pc/tests/ pi/tests/
```

## Licenza

MIT – vedi [LICENSE](LICENSE).

