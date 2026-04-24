# Installation Guide – DroneBot 2026

## Prerequisites

| Component | Minimum version |
|-----------|----------------|
| Python    | 3.10            |
| pip       | 23              |
| Git       | 2.x             |

---

## 1. Clone the repository

```bash
git clone https://github.com/akkaso/Dronebote-2026.git
cd Dronebote-2026
```

---

## 2. PC setup (development machine / laptop)

```bash
python3 -m venv .venv-pc
source .venv-pc/bin/activate      # Windows: .venv-pc\Scripts\activate
pip install -r requirements-pc.txt
```

Verify:

```bash
python3 -c "import cv2, numpy, websockets, yaml; print('OK')"
```

---

## 3. Raspberry Pi setup

Copy the repository to the Pi:

```bash
scp -r . pi@<PI_IP>:/home/pi/Dronebote-2026
```

On the Pi:

```bash
cd /home/pi/Dronebote-2026
python3 -m venv .venv-pi
source .venv-pi/bin/activate
pip install -r requirements-pi.txt
```

---

## 4. GPIO wiring (Raspberry Pi)

| Function | BCM pin |
|----------|---------|
| Forward  | 17      |
| Left     | 27      |
| Right    | 22      |
| Back     | 10      |
| Stop     | 9       |

Connect each pin through a suitable driver circuit (e.g. L298N motor driver).

---

## 5. Run with Docker (optional)

```bash
docker-compose up --build
```

This starts the Pi mock server and PC mock client automatically.

---

## 6. Run tests

```bash
# PC tests
pip install -r requirements-pc.txt
pytest pc/tests/

# Pi tests (mock – no hardware needed)
pytest pi/tests/
```

---

## 7. systemd service (Raspberry Pi auto-start)

```bash
sudo cp pi/systemd/dronbot_pi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dronbot_pi
sudo systemctl start dronbot_pi
```
