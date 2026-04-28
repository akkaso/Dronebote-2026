# Guida Completa all'Installazione – DroneBot 2026

Questa guida ti accompagna passo dopo passo nell'installazione e configurazione del sistema DroneBot 2026 su entrambe le macchine: **PC (sviluppo/visione)** e **Raspberry Pi (controllo motori)**.

---

## Indice

1. [Requisiti di sistema](#1-requisiti-di-sistema)
2. [Clonare la repository](#2-clonare-la-repository)
3. [Installazione sul PC](#3-installazione-sul-pc)
4. [Installazione sul Raspberry Pi](#4-installazione-sul-raspberry-pi)
5. [Cablaggio GPIO](#5-cablaggio-gpio)
6. [Prima esecuzione (demo senza hardware)](#6-prima-esecuzione-demo-senza-hardware)
7. [Esecuzione reale (PC + Pi connessi)](#7-esecuzione-reale-pc--pi-connessi)
8. [Configurazione avanzata](#8-configurazione-avanzata)
9. [Servizio systemd su Raspberry Pi](#9-servizio-systemd-su-raspberry-pi)
10. [Avvio con Docker (opzionale)](#10-avvio-con-docker-opzionale)
11. [Esecuzione dei test](#11-esecuzione-dei-test)
12. [Risoluzione dei problemi](#12-risoluzione-dei-problemi)

---

## 1. Requisiti di sistema

### PC (qualsiasi sistema operativo)

| Componente | Versione minima | Note |
|------------|----------------|------|
| Python     | 3.10            | [python.org](https://python.org) |
| pip        | 23+             | `pip install --upgrade pip` |
| Git        | 2.x             | [git-scm.com](https://git-scm.com) |
| OpenCV     | 4.7+            | installato via pip |
| RAM        | 2 GB            | |
| OS         | Windows 10+ / macOS 12+ / Ubuntu 20.04+ | |

### Raspberry Pi

| Componente | Versione minima | Note |
|------------|----------------|------|
| Raspberry Pi | 3B+ o superiore | Pi 4 consigliato |
| Raspberry Pi OS | Bullseye o Bookworm | 64-bit consigliato |
| Python     | 3.10            | preinstallato su Bookworm |
| RPi.GPIO   | 0.7+            | solo su hardware Pi reale |
| Connessione di rete | qualsiasi | per comunicare con il PC |

---

## 2. Clonare la repository

Sul **PC** (e/o sul **Raspberry Pi**):

```bash
git clone https://github.com/akkaso/Dronebote-2026.git
cd Dronebote-2026
```

> **Nota per Windows**: usa Git Bash o WSL2 per eseguire gli script `.sh`.

---

## 3. Installazione sul PC

### 3.1 Crea un ambiente virtuale

```bash
python3 -m venv .venv-pc
```

### 3.2 Attiva l'ambiente virtuale

**Linux / macOS:**
```bash
source .venv-pc/bin/activate
```

**Windows (PowerShell):**
```powershell
.venv-pc\Scripts\Activate.ps1
```

**Windows (cmd):**
```cmd
.venv-pc\Scripts\activate.bat
```

### 3.3 Installa le dipendenze PC

```bash
pip install --upgrade pip
pip install -r requirements-pc.txt
```

Le dipendenze installate sono:
- `opencv-python` – cattura video e rilevamento fuoco
- `numpy` – operazioni su array
- `websockets` – comunicazione con il Pi
- `pyyaml` – lettura di config.yaml
- `pytest` – esecuzione dei test

### 3.4 Verifica l'installazione

```bash
python3 -c "import cv2, numpy, websockets, yaml; print('✅ Tutte le dipendenze OK')"
python3 -c "import cv2; print('OpenCV versione:', cv2.__version__)"
```

Dovresti vedere:
```
✅ Tutte le dipendenze OK
OpenCV versione: 4.x.x
```

### 3.5 Genera il video di test

```bash
python3 scripts/genera_video_esempio.py
```

Questo crea:
- `sample_video.mp4` – video sintetico con blob di fuoco e marker ArUco
- `pc/sample_frames/frame_00*.jpg` – 10 frame statici di riserva

---

## 4. Installazione sul Raspberry Pi

### 4.1 Copia il progetto sul Pi

Dal **PC**, tramite SCP:
```bash
scp -r . pi@<IP_DEL_PI>:/home/pi/Dronebote-2026
```

Oppure clona direttamente **sul Pi**:
```bash
# sul Raspberry Pi
git clone https://github.com/akkaso/Dronebote-2026.git
cd Dronebote-2026
```

### 4.2 Trova l'indirizzo IP del Raspberry Pi

Sul Pi:
```bash
hostname -I
# esempio output: 192.168.1.42
```

Oppure da router/DHCP, o con `ping raspberrypi.local` se hai avahi/mDNS attivo.

### 4.3 Crea un ambiente virtuale sul Pi

```bash
python3 -m venv .venv-pi
source .venv-pi/bin/activate
```

### 4.4 Installa le dipendenze Pi

```bash
pip install --upgrade pip
pip install -r requirements-pi.txt
```

Le dipendenze installate sono:
- `websockets` – server WebSocket
- `RPi.GPIO` – controllo pin GPIO (solo su hardware Pi reale; ignorato in modalità mock)
- `pytest` – esecuzione dei test

> **Nota**: su Pi 5 o ambienti virtuali, `RPi.GPIO` potrebbe richiedere:
> ```bash
> sudo apt-get install python3-dev
> ```

### 4.5 Verifica l'installazione sul Pi

```bash
python3 -c "import websockets; print('✅ websockets OK')"
# Su hardware Pi reale:
python3 -c "import RPi.GPIO; print('✅ RPi.GPIO OK')"
```

---

## 5. Cablaggio GPIO

Collega i pin GPIO del Raspberry Pi al tuo circuito di controllo motori
(es. driver L298N, L293D, o scheda motor driver compatibile).

| Funzione | Pin BCM | Pin fisico (header 40-pin) |
|----------|---------|---------------------------|
| Avanti   | GPIO 17 | Pin 11                    |
| Sinistra | GPIO 27 | Pin 13                    |
| Destra   | GPIO 22 | Pin 15                    |
| Indietro | GPIO 10 | Pin 19                    |
| Stop     | GPIO 9  | Pin 21                    |
| GND      | GND     | Pin 6, 9, 14, 20, 25, ... |

### Schema tipico con L298N

```
Raspberry Pi GPIO ──► L298N IN1/IN2/IN3/IN4 ──► Motori DC
         GND ──────► L298N GND
    (5V esterno) ──► L298N 12V (alimentazione motori)
```

> ⚠️ **Attenzione**: non collegare i motori direttamente ai pin GPIO del Pi.
> Usa sempre un driver motori intermedio per proteggere il Pi.

---

## 6. Prima esecuzione (demo senza hardware)

Questa modalità funziona su qualsiasi computer, senza Pi né telecamera.

```bash
# Assicurati di avere l'ambiente PC attivo
source .venv-pc/bin/activate   # Linux/macOS

# Genera il video di test (se non già fatto)
python3 scripts/genera_video_esempio.py

# Avvia la demo completa (server Pi mock + client PC mock)
bash scripts/esecuzione_esempio.sh
```

Vedrai nel terminale i log di:
- il server Pi mock che riceve comandi
- il client PC che rileva il fuoco e invia comandi
- i frame di debug salvati in `pc/debug/`

---

## 7. Esecuzione reale (PC + Pi connessi)

### 7.1 Avvia il server sul Raspberry Pi

Sul **Raspberry Pi** (hardware GPIO reale):
```bash
cd /home/pi/Dronebote-2026
source .venv-pi/bin/activate
bash pi/avvia_pi.sh --host 0.0.0.0 --port 8765
```

Sul **Raspberry Pi** (modalità mock, senza motori):
```bash
bash pi/avvia_pi.sh --host 0.0.0.0 --port 8765 --mock
```

Il server è pronto quando vedi:
```
INFO pi_ws_server: Avvio server WebSocket su 0.0.0.0:8765 ...
```

### 7.2 Avvia il client sul PC

Apri un **secondo terminale** sul PC. Sostituisci `<IP_DEL_PI>` con l'IP del tuo Pi:

**Da un file video:**
```bash
bash pc/avvia_pc.sh --source sample_video.mp4 --ws ws://<IP_DEL_PI>:8765
```

**Da una webcam USB (dispositivo 0):**
```bash
bash pc/avvia_pc.sh --source 0 --ws ws://<IP_DEL_PI>:8765
```

**Da uno stream RTSP (telecamera IP):**
```bash
bash pc/avvia_pc.sh --source rtsp://<IP_TELECAMERA>/stream --ws ws://<IP_DEL_PI>:8765
```

**Modalità mock PC (nessun WebSocket, nessun display):**
```bash
bash pc/avvia_pc.sh --source sample_video.mp4 --mock --no-display --debug
```

### 7.3 Finestra di visualizzazione

Se non hai usato `--no-display`, si aprirà una finestra OpenCV che mostra:
- il frame video in diretta
- il cerchio rosso sul centroide del fuoco
- il comando corrente (es. `CMD: forward 0.35s`)
- il contatore FPS

Premi **`q`** per uscire.

---

## 8. Configurazione avanzata

Modifica `pc/config.yaml` per adattare il sistema:

```yaml
# Sogliatura HSV per il fuoco (regola in base all'illuminazione)
fire_hsv_lower: [0, 120, 120]   # H_min, S_min, V_min
fire_hsv_upper: [30, 255, 255]  # H_max, S_max, V_max
min_contour_area: 500           # ignora blob più piccoli di N pixel²

# Guadagni PID
pid_kp: 0.8    # proporzionale – aumenta per risposta più rapida
pid_ki: 0.05   # integrale – riduce l'errore stazionario
pid_kd: 0.1    # derivativo – attenua le oscillazioni

# Navigazione
turn_threshold: 40    # errore laterale (px) sotto cui va dritto
base_duration: 0.3    # durata minima di ogni comando (secondi)

# WebSocket
ws_url: "ws://192.168.1.42:8765"  # IP del Raspberry Pi

# Telecamera
camera_index: 0       # indice dispositivo (0 = prima webcam)

# Debug
debug_save: true      # salva frame annotati in pc/debug/
display: true         # mostra finestra OpenCV
```

### Calibrazione HSV per il fuoco

Per trovare i valori HSV corretti per il tuo ambiente:

```python
import cv2
import numpy as np

def nothing(x): pass

cap = cv2.VideoCapture(0)  # o il tuo file video
cv2.namedWindow("Calibrazione HSV")
cv2.createTrackbar("H_min", "Calibrazione HSV", 0, 179, nothing)
cv2.createTrackbar("H_max", "Calibrazione HSV", 30, 179, nothing)
cv2.createTrackbar("S_min", "Calibrazione HSV", 120, 255, nothing)
cv2.createTrackbar("V_min", "Calibrazione HSV", 120, 255, nothing)

while True:
    _, frame = cap.read()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h_min = cv2.getTrackbarPos("H_min", "Calibrazione HSV")
    h_max = cv2.getTrackbarPos("H_max", "Calibrazione HSV")
    s_min = cv2.getTrackbarPos("S_min", "Calibrazione HSV")
    v_min = cv2.getTrackbarPos("V_min", "Calibrazione HSV")
    maschera = cv2.inRange(hsv, (h_min, s_min, v_min), (h_max, 255, 255))
    cv2.imshow("Calibrazione HSV", maschera)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 9. Servizio systemd su Raspberry Pi

Per avviare automaticamente il server Pi all'accensione:

### 9.1 Copia il file di servizio

```bash
sudo cp /home/pi/Dronebote-2026/pi/systemd/dronbot_pi.service /etc/systemd/system/
```

### 9.2 Modifica il percorso se necessario

```bash
sudo nano /etc/systemd/system/dronbot_pi.service
```

Verifica che `WorkingDirectory` e `ExecStart` puntino al percorso corretto del tuo utente.

### 9.3 Abilita e avvia il servizio

```bash
sudo systemctl daemon-reload
sudo systemctl enable dronbot_pi   # avvio automatico al boot
sudo systemctl start dronbot_pi    # avvio immediato
```

### 9.4 Controlla lo stato

```bash
sudo systemctl status dronbot_pi
journalctl -u dronbot_pi -f         # log in diretta
```

### 9.5 Ferma o disabilita il servizio

```bash
sudo systemctl stop dronbot_pi
sudo systemctl disable dronbot_pi
```

---

## 10. Avvio con Docker (opzionale)

Richiede Docker e Docker Compose installati.

```bash
# Costruisci e avvia entrambi i container (PC mock + Pi mock)
docker-compose up --build

# Solo il server Pi
docker-compose up pi

# Solo il client PC
docker-compose up pc
```

Per usare una sorgente video reale con Docker, modifica `docker-compose.yml`
e aggiungi il dispositivo `/dev/video0` al servizio PC.

---

## 11. Esecuzione dei test

I test verificano la correttezza del codice senza richiedere hardware.

```bash
# Attiva il venv PC
source .venv-pc/bin/activate

# Tutti i test (PC + Pi)
pytest pc/tests/ pi/tests/ -v

# Solo test PID
pytest pc/tests/test_pid.py -v

# Solo test ArUco
pytest pc/tests/test_aruco.py -v

# Solo test GPIO mock
pytest pi/tests/test_gpio_mock.py -v
```

Output atteso: **26 test superati**.

---

## 12. Risoluzione dei problemi

### ❌ `import cv2` fallisce

```bash
pip install opencv-python
# oppure, se hai già una versione:
pip install --upgrade opencv-python
```

### ❌ `RPi.GPIO` non disponibile sul PC

Normale: `RPi.GPIO` funziona solo su Raspberry Pi. Usa `--mock` sul PC:
```bash
bash pi/avvia_pi.sh --mock
```

### ❌ Connessione WebSocket rifiutata

1. Verifica che il server Pi sia in esecuzione: `sudo systemctl status dronbot_pi`
2. Controlla il firewall del Pi: `sudo ufw allow 8765`
3. Verifica l'IP del Pi: `hostname -I`
4. Prova il ping: `ping <IP_DEL_PI>`

### ❌ Nessun fuoco rilevato nel video

1. Controlla i valori HSV in `pc/config.yaml`
2. Abilita `debug_save: true` e guarda i frame in `pc/debug/`
3. Riduci `min_contour_area` se il blob è piccolo
4. Usa lo script di calibrazione HSV sopra

### ❌ La finestra OpenCV non si apre

Su server headless o container Docker, usa `--no-display`:
```bash
bash pc/avvia_pc.sh --source sample_video.mp4 --no-display --debug
```

### ❌ Errori `permission denied` su GPIO

```bash
sudo usermod -a -G gpio $USER
# poi riavvia la sessione
```

### ❌ Video sintetico non generato correttamente

```bash
python3 -c "import cv2; print(cv2.getBuildInformation())"
# controlla che FFMPEG sia abilitato
```

---

## Contatti e Supporto

Per problemi o domande, apri una issue su:
[https://github.com/akkaso/Dronebote-2026/issues](https://github.com/akkaso/Dronebote-2026/issues)
