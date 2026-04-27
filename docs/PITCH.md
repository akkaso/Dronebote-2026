# DroneBot 2026 – Presentazione del Progetto

## Il Problema

In situazioni di emergenza (incendi, ambienti pericolosi), i soccorritori hanno bisogno di un modo
per localizzare e raggiungere rapidamente una sorgente di fuoco senza mettere a rischio vite umane.

## La Nostra Soluzione

**DroneBot 2026** è un rover terrestre autonomo che:

1. **Vede** – utilizza una telecamera collegata e OpenCV per rilevare il fuoco in tempo reale tramite
   segmentazione del colore in spazio HSV e filtraggio morfologico.
2. **Ragiona** – un controllore PID calcola la correzione laterale; un modulo di navigazione
   la converte in comandi discreti per i motori (avanti / sinistra / destra).
3. **Agisce** – un Raspberry Pi riceve i comandi via WebSocket e aziona i motori del rover
   tramite GPIO.

## Caratteristiche Principali

| Funzionalità | Dettaglio |
|-------------|-----------|
| Rilevamento fuoco in tempo reale | HSV + morfologia + contorni, ~30 fps |
| Stima posa ArUco | Localizzazione del rover rispetto ai marker |
| PID con anti-windup | Correzione laterale fluida e stabile |
| Arresto di emergenza | Fermata immediata, rifiuto comandi successivi |
| Modalità mock | Pipeline completa testabile senza hardware |
| WebSocket ack/retry | Consegna affidabile dei comandi |
| Docker ready | Un solo comando per avviare entrambi i servizi |

## Architettura

```
Telecamera → OpenCV (PC) → PID → WebSocket → RPi.GPIO → Motori
```

## Perché Python 3.10+?

- Pattern matching strutturale (per utilizzi futuri)
- Tipi unione con `|` (type hints più puliti)
- Ampiamente disponibile su Raspberry Pi OS Bookworm

## Rilevanza per la Competizione

DroneBot 2026 dimostra:
- Fusione sensoriale (visione + marker di posa)
- Loop di controllo in tempo reale
- Programmazione Linux embedded / GPIO
- Comunicazione di rete affidabile

## Sviluppi Futuri

- [ ] Integrazione telecamera di profondità 3D (RealSense)
- [ ] Prioritizzazione di più sorgenti di fuoco
- [ ] Ritorno autonomo alla base dopo l'estinzione
- [ ] Integrazione con ROS 2

