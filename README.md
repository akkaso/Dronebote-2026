# DroneBot 2026

> 🚀 **Il codice completo del progetto si trova nel ramo [`project-dronebot-2026`](../../tree/project-dronebot-2026).**
> Passa a quel ramo per trovare tutto il codice sorgente, la documentazione e le istruzioni di avvio.

---

## Cos'è DroneBot 2026?

DroneBot 2026 è un sistema robotico a guida autonoma sviluppato per **RomeCup 2026**.  
Il robot individua autonomamente sorgenti di fuoco tramite **visione artificiale** (lato PC) e si avvicina ad esse controllando i motori tramite un **Raspberry Pi** (lato Pi).  
La comunicazione tra PC e Pi avviene in tempo reale via **WebSocket**.

---

## Architettura del sistema

```
[Telecamera / Sorgente Video]
        |
      [PC]  ← Rilevamento fuoco (OpenCV + sogliatura HSV)
               Stima posa con marker ArUco
               Controllore PID per la navigazione
        |
        |  WebSocket (comandi JSON: avanti / sinistra / destra / stop)
        |
      [Pi]  ← Server WebSocket su Raspberry Pi
               Controllo motori via GPIO
               Arresto di emergenza
```

---

## Funzionalità principali

| Componente | Descrizione |
|---|---|
| 🔥 Rilevamento fuoco | Sogliatura colore HSV su frame video in tempo reale |
| 📐 Stima posa | Marker ArUco per calcolare distanza e angolo dal fuoco |
| 🎛️ Controllo PID | Guadagni configurabili (Kp, Ki, Kd) con anti-windup |
| 📡 WebSocket | Comunicazione bidirezionale PC ↔ Pi con heartbeat e retry |
| 🤖 GPIO | Controllo diretto dei motori su Raspberry Pi (reale o mock) |
| 🛑 Emergenza | Comando `emergency_stop` per fermare immediatamente i motori |
| 🐳 Docker | `docker-compose up` per avviare l'intero sistema |
| 🧪 Test | Suite pytest per PC e Pi (`pytest pc/tests/ pi/tests/`) |

---

## Struttura del progetto (ramo `project-dronebot-2026`)

```
.
├── pc/                  # Visione artificiale e client WebSocket (lato PC)
│   ├── vision_client.py
│   ├── aruco_detector.py
│   ├── pid.py
│   ├── navigation.py
│   ├── ws_client.py
│   ├── config.yaml
│   └── tests/
├── pi/                  # Server WebSocket e controllo GPIO (lato Pi)
│   ├── pi_ws_server.py
│   ├── gpio_controller.py
│   └── tests/
├── docs/                # Guide installazione, uso e presentazione
├── scripts/             # Script di avvio e generazione video di test
├── docker-compose.yml
├── requirements-pc.txt
└── requirements-pi.txt
```

---

## Come iniziare

👉 Vai al ramo **[`project-dronebot-2026`](../../tree/project-dronebot-2026)** e segui le istruzioni nel `README.md` lì presente.

---

## Licenza

MIT
