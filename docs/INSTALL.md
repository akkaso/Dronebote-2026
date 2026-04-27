# Guida all'Installazione – DroneBot 2026

## Prerequisiti

| Componente | Versione minima |
|------------|----------------|
| Python     | 3.10            |
| pip        | 23              |
| Git        | 2.x             |

---

## 1. Clona la repository

```bash
git clone https://github.com/akkaso/Dronebote-2026.git
cd Dronebote-2026
```

---

## 2. Configurazione PC (portatile / desktop di sviluppo)

```bash
python3 -m venv .venv-pc
source .venv-pc/bin/activate      # Windows: .venv-pc\Scripts\activate
pip install -r requirements-pc.txt
```

Verifica l'installazione:

```bash
python3 -c "import cv2, numpy, websockets, yaml; print('OK')"
```

---

## 3. Configurazione Raspberry Pi

Copia la repository sul Pi:

```bash
scp -r . pi@<IP_DEL_PI>:/home/pi/Dronebote-2026
```

Sul Raspberry Pi:

```bash
cd /home/pi/Dronebote-2026
python3 -m venv .venv-pi
source .venv-pi/bin/activate
pip install -r requirements-pi.txt
```

---

## 4. Cablaggio GPIO (Raspberry Pi)

| Funzione | Pin BCM |
|----------|---------|
| Avanti   | 17      |
| Sinistra | 27      |
| Destra   | 22      |
| Indietro | 10      |
| Stop     | 9       |

Collega ogni pin tramite un circuito driver adeguato (es. driver motori L298N).

---

## 5. Avvio con Docker (opzionale)

```bash
docker-compose up --build
```

Questo comando avvia automaticamente il server Pi mock e il client PC mock.

---

## 6. Esecuzione dei test

```bash
# Test PC
pip install -r requirements-pc.txt
pytest pc/tests/

# Test Pi (mock – nessun hardware necessario)
pytest pi/tests/
```

---

## 7. Servizio systemd (avvio automatico su Raspberry Pi)

```bash
sudo cp pi/systemd/dronbot_pi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dronbot_pi
sudo systemctl start dronbot_pi
```

