# Usage Guide – DroneBot 2026

## Quick demo (no hardware)

```bash
# 1. Generate a synthetic test video
python3 scripts/generate_sample_video.py

# 2. Start Pi mock server + PC mock client
bash scripts/sample_run.sh
```

---

## Running manually

### Start the Pi server (on Raspberry Pi or mock)

```bash
# Real GPIO (Raspberry Pi only)
bash pi/run_pi.sh --host 0.0.0.0 --port 8765

# Mock mode (any machine)
bash pi/run_pi.sh --host 0.0.0.0 --port 8765 --mock
```

### Start the PC client

```bash
# From a video file
bash pc/run_pc.sh --source sample_video.mp4 --ws ws://<PI_IP>:8765

# From a webcam (device 0)
bash pc/run_pc.sh --source 0 --ws ws://<PI_IP>:8765

# From an RTSP stream
bash pc/run_pc.sh --source rtsp://camera-ip/stream --ws ws://<PI_IP>:8765

# Mock mode (no WebSocket)
bash pc/run_pc.sh --source sample_video.mp4 --mock --no-display
```

---

## Configuration

Edit `pc/config.yaml` to adjust:

- `fire_hsv_lower` / `fire_hsv_upper` – tune HSV range for your lighting conditions.
- `pid_kp`, `pid_ki`, `pid_kd` – adjust PID response.
- `turn_threshold` – lateral pixel error before the rover turns instead of going forward.
- `debug_save` – set to `true` to save annotated frames in `pc/debug/`.

---

## Emergency stop

Send an emergency stop at any time from the PC:

```python
import asyncio, websockets, json

async def estop():
    async with websockets.connect("ws://localhost:8765") as ws:
        await ws.send(json.dumps({"cmd": "emergency_stop", "msg_id": "estop-001"}))
        print(await ws.recv())

asyncio.run(estop())
```

The Pi server will stop all motors and reject further movement commands until restarted.

---

## Debug frames

When `debug_save: true`, annotated frames are saved to `pc/debug/frame_XXXXXX.jpg`.
They show the fire centroid, command overlay, and FPS counter.

---

## Running tests

```bash
pytest pc/tests/ pi/tests/ -v
```
