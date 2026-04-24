# DroneBot 2026

DroneBot 2026 is an autonomous ground rover system that detects fire using computer vision (PC) and drives toward it using a Raspberry Pi GPIO-controlled vehicle. Communication between the PC and Pi uses WebSockets.

## Architecture

```
[Camera / Video Source]
        |
      [PC]  ← OpenCV fire detection + ArUco pose estimation
        |       ↓ WebSocket (JSON commands)
      [Pi]  ← GPIO motor control
```

- **PC side**: captures video, detects fire with HSV thresholding, estimates position with ArUco markers, sends discrete commands (forward/left/right/stop) with duration via WebSocket.
- **Pi side**: receives commands, drives motors via GPIO, sends acknowledgements, supports emergency stop.

## Quick Start

### Requirements

- Python 3.10+
- PC: `pip install -r requirements-pc.txt`
- Pi: `pip install -r requirements-pi.txt`

### Generate test video

```bash
python3 scripts/generate_sample_video.py
```

### Run demo (both mock PC client + mock Pi server)

```bash
bash scripts/sample_run.sh
```

### Run Pi server (on Raspberry Pi)

```bash
bash pi/run_pi.sh --host 0.0.0.0 --port 8765
```

### Run PC client

```bash
bash pc/run_pc.sh --source sample_video.mp4 --ws ws://localhost:8765
```

Edit `pc/config.yaml` to customise parameters.

## Docker

```bash
docker-compose up
```

## Project Structure

```
.
├── pc/                    # PC-side vision + control
│   ├── vision_client.py   # Main CLI entry-point
│   ├── aruco_detector.py  # ArUco marker detection & pose estimation
│   ├── pid.py             # PID controller with anti-windup
│   ├── navigation.py      # Converts PID output to discrete commands
│   ├── ws_client.py       # WebSocket client with ack/retry/heartbeat
│   ├── utils.py           # Shared helpers
│   ├── config.yaml        # Tunable parameters
│   ├── Dockerfile
│   ├── run_pc.sh
│   ├── sample_frames/     # Fallback still frames
│   ├── debug/             # Saved debug frames
│   └── tests/
│       ├── test_pid.py
│       └── test_aruco.py
├── pi/                    # Raspberry Pi GPIO server
│   ├── pi_ws_server.py    # WebSocket server
│   ├── gpio_controller.py # GPIO control (real + mock)
│   ├── Dockerfile
│   ├── run_pi.sh
│   ├── systemd/
│   │   └── dronbot_pi.service
│   └── tests/
│       └── test_gpio_mock.py
├── docs/
│   ├── INSTALL.md
│   ├── USAGE.md
│   ├── PITCH.md
│   └── pseudocode.txt
├── scripts/
│   ├── sample_run.sh
│   └── generate_sample_video.py
├── ci/
│   └── github-actions.yml
├── .github/workflows/     # CI (symlinked from ci/)
├── requirements-pc.txt
├── requirements-pi.txt
├── docker-compose.yml
├── flowchart.txt
└── sample_video.mp4       # placeholder / generated
```

## Configuration

All tunable parameters live in `pc/config.yaml`:

- `fire_hsv_lower` / `fire_hsv_upper`: HSV range for fire colour detection
- `min_contour_area`: minimum pixel area to count as fire
- `pid_kp/ki/kd`: PID gains
- `ws_url`: WebSocket server address
- `camera_index`: local camera device index
- `debug_save`: save annotated debug frames to `pc/debug/`

## Safety

- **Emergency stop**: sending `{"cmd":"emergency_stop"}` to the Pi server immediately stops all motors and ignores further movement commands until the process is restarted.
- **Mock mode**: both PC and Pi support `--mock` flag so the full pipeline can be tested without hardware.
- **Heartbeat**: PC client sends periodic pings; Pi server disconnects unresponsive clients.

## Tests

```bash
pytest pc/tests/ pi/tests/
```

## License

MIT – see [LICENSE](LICENSE).
