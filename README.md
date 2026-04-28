# DroneBot 2026 – ROMECUP @ Sapienza

Competizione DroneBot, RomeCup 2026, Fondazione Mondo Digitale – Sapienza Università di Roma, 28-29 Aprile 2026.

---

## Descrizione tecnica della soluzione

Il sistema realizzato integra un drone **DJI NEO 1**, un rover RC modificato e un'architettura software distribuita su due nodi: un **PC di controllo** (vision + logica di missione) e un **Raspberry Pi** a bordo del rover (attuazione GPIO).

### Architettura generale

```
┌──────────────┐  video stream  ┌───────────────────────┐
│  DJI NEO 1   │ ─────────────► │  PC – Vision & Control│
│  (telecamera)│                │  fire_detector.py     │
└──────────────┘                │  aruco_tracker.py     │
                                │  main.py              │
                                └──────────┬────────────┘
                                           │ UDP socket (comandi direzionali)
                                           ▼
                                ┌──────────────────────┐
                                │  Raspberry Pi (rover)│
                                │  rover_server.py     │
                                │  GPIO → Arduino      │
                                │  Arduino → RC TX hack│
                                └──────────────────────┘
```

### Fase 1 – Riconoscimento del fuoco (Fire Detection)

Il modulo `pc/fire_detector.py` elabora ogni frame del flusso video del drone tramite **OpenCV**.  
Il riconoscimento avviene in spazio colore **HSV**: le soglie per i toni arancio/rosso/giallo tipici di un'immagine di fuoco vengono configurate in `pc/config.yaml`.  
Viene calcolata l'area del contorno più grande che supera una soglia minima; se l'area supera la soglia di confidenza, la regione viene marcata come *fuoco rilevato* e ne vengono restituite le coordinate del baricentro nel frame.  
L'approccio non utilizza librerie proprietarie né modelli pre-addestrati di terze parti: tutto il codice di riconoscimento è scritto e compilabile dagli studenti.

**Punti di forza:**
- Nessuna dipendenza da cloud o modelli commerciali.
- Robustezza alla variazione di luminosità tramite normalizzazione del canale V in HSV.
- Latenza <20 ms su hardware consumer (testato su CPU Intel i5 con risoluzione 720p).

### Fase 2 – Guida semi-automatica del rover tramite ArUco

Il modulo `pc/aruco_tracker.py` individua in ogni frame il **marker ArUco** posizionato sul rover, stima l'offset (Δx, Δy in pixel) del centro del marker rispetto al centro del frame, e ricava un vettore di errore.  
`pc/main.py` implementa un **controller proporzionale** (P-controller) che traduce l'errore in comandi discreti (AVANTI / INDIETRO / SINISTRA / DESTRA / STOP) inviati via **socket UDP** al Raspberry Pi.  
Il Raspberry Pi (`pi/rover_server.py`) riceve i comandi e li mappa su uscite GPIO collegate a un **Arduino**, il quale pilota i quattro canali del trasmettitore RC bypassando i pulsanti fisici.

**Punti di forza:**
- Loop di controllo chiuso: il drone "vede" il rover e corregge continuamente la traiettoria.
- Architettura modulare: i parametri (soglie, guadagno proporzionale, indirizzo IP, pin GPIO) sono tutti configurabili senza ricompilare il codice.
- Fail-safe: se il marker ArUco non viene rilevato per più di N frame consecutivi (configurabile), il rover si ferma automaticamente.

### Innovazioni tecnologiche

1. **Dual-detection pipeline**: fire detection e ArUco tracking girano in parallelo su thread separati, riducendo la latenza complessiva del loop di controllo.
2. **Auto-calibrazione HSV**: all'avvio, il sistema acquisisce un campione del frame e adatta automaticamente le soglie superiori/inferiori del canale H in funzione della temperatura colore dell'illuminazione ambientale.
3. **RC hack tramite Arduino**: il radiocomando del rover viene modificato inserendo optoaccoppiatori in parallelo ai pulsanti; l'Arduino emette segnali TTL controllati dal Raspberry Pi, mantenendo intatta la funzionalità manuale del telecomando.

---

## Flowchart della pipeline

```
START
  │
  ▼
Inizializza stream video DJI NEO 1
  │
  ▼
┌─────────────────────────────────────────┐
│  LOOP PRINCIPALE (ogni frame)           │
│                                         │
│  ┌──────────────────┐                   │
│  │ Fire Detection   │                   │
│  │ (HSV threshold)  │                   │
│  └────────┬─────────┘                   │
│           │ fuoco rilevato?             │
│           ├─── NO  ──► continua loop    │
│           │                             │
│           ▼ SÌ                          │
│  Registra posizione fuoco nel frame     │
│           │                             │
│  ┌────────▼──────────┐                  │
│  │ ArUco Detection   │                  │
│  │ (cv2.aruco)       │                  │
│  └────────┬──────────┘                  │
│           │ marker trovato?             │
│           ├─── NO  ──► STOP rover       │
│           │                             │
│           ▼ SÌ                          │
│  Calcola errore (Δx, Δy)               │
│           │                             │
│  ┌────────▼──────────┐                  │
│  │ P-Controller      │                  │
│  │ errore → comando  │                  │
│  └────────┬──────────┘                  │
│           │                             │
│  Invia comando UDP al Raspberry Pi      │
│           │                             │
│  Rover nell'area fuoco?                 │
│           ├─── SÌ ──► STOP / MISSIONE   │
│           │            COMPLETATA       │
│           └─── NO ──► continua loop     │
└─────────────────────────────────────────┘
  │
  ▼
END
```

---

## Struttura della repository

```
├── pc/
│   ├── main.py            # Loop principale missione
│   ├── fire_detector.py   # Riconoscimento immagine fuoco (HSV)
│   ├── aruco_tracker.py   # Stima posizione marker ArUco
│   ├── config.yaml        # Parametri configurabili
│   └── tests/
│       ├── test_fire_detector.py
│       └── test_aruco_tracker.py
├── pi/
│   ├── rover_server.py    # Server GPIO su Raspberry Pi
│   └── tests/
│       └── test_rover_server.py
└── docs/
    ├── BOM.md             # Bill of Materials
    └── SBOM.md            # Software Bill of Materials
```

## Requisiti software

```
pip install opencv-python opencv-contrib-python numpy pyyaml RPi.GPIO
```

## Esecuzione

```bash
# Sul Raspberry Pi (rover):
python pi/rover_server.py

# Sul PC di controllo:
python pc/main.py
```

## Test

```bash
pytest pc/tests/ pi/tests/
```
