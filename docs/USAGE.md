# Guida all'Uso – DroneBot 2026

## Demo rapida (senza hardware)

```bash
# 1. Genera un video di test sintetico
python3 scripts/genera_video_esempio.py

# 2. Avvia il server Pi mock + il client PC mock
bash scripts/esecuzione_esempio.sh
```

---

## Esecuzione manuale

### Avvia il server Pi (su Raspberry Pi o in modalità mock)

```bash
# GPIO reale (solo Raspberry Pi)
bash pi/avvia_pi.sh --host 0.0.0.0 --port 8765

# Modalità mock (qualsiasi computer)
bash pi/avvia_pi.sh --host 0.0.0.0 --port 8765 --mock
```

### Avvia il client PC

```bash
# Da un file video
bash pc/avvia_pc.sh --source sample_video.mp4 --ws ws://<IP_DEL_PI>:8765

# Da una webcam (dispositivo 0)
bash pc/avvia_pc.sh --source 0 --ws ws://<IP_DEL_PI>:8765

# Da uno stream RTSP
bash pc/avvia_pc.sh --source rtsp://ip-telecamera/stream --ws ws://<IP_DEL_PI>:8765

# Modalità mock (nessun WebSocket)
bash pc/avvia_pc.sh --source sample_video.mp4 --mock --no-display
```

---

## Configurazione

Modifica `pc/config.yaml` per regolare:

- `fire_hsv_lower` / `fire_hsv_upper` – intervallo HSV adatto alle condizioni di luce.
- `pid_kp`, `pid_ki`, `pid_kd` – risposta del controllore PID.
- `turn_threshold` – errore laterale in pixel oltre cui il rover gira invece di andare dritto.
- `debug_save` – imposta `true` per salvare i frame annotati in `pc/debug/`.

---

## Arresto di emergenza

Invia un arresto di emergenza in qualsiasi momento dal PC:

```python
import asyncio, websockets, json

async def stop_emergenza():
    async with websockets.connect("ws://localhost:8765") as ws:
        await ws.send(json.dumps({"cmd": "emergency_stop", "msg_id": "stop-001"}))
        print(await ws.recv())

asyncio.run(stop_emergenza())
```

Il server Pi fermerà tutti i motori e rifiuterà ulteriori comandi di movimento fino al riavvio.

---

## Frame di debug

Quando `debug_save: true`, i frame annotati vengono salvati in `pc/debug/frame_XXXXXX.jpg`.
Mostrano il centroide del fuoco, il comando corrente e il contatore FPS.

---

## Esecuzione dei test

```bash
pytest pc/tests/ pi/tests/ -v
```

