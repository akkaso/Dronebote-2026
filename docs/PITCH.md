# DroneBot 2026 – Project Pitch

## The Problem

In emergency situations (fires, hazardous environments), first responders need a way
to quickly locate and approach a fire source without putting humans at risk.

## Our Solution

**DroneBot 2026** is an autonomous ground rover that:

1. **Sees** – uses a connected camera and OpenCV to detect fire in real time using
   colour-based HSV segmentation and morphological filtering.
2. **Thinks** – a PID controller computes lateral correction; a navigation module
   converts this to discrete motor commands (forward / left / right).
3. **Acts** – a Raspberry Pi receives commands via WebSocket and drives the rover
   motors through GPIO.

## Key Features

| Feature | Detail |
|---------|--------|
| Real-time fire detection | HSV + morphology + contour, ~30 fps |
| ArUco pose estimation | Localise the rover relative to markers |
| PID with anti-windup | Smooth, stable lateral correction |
| Emergency stop | Instant halt, rejects further movement |
| Mock mode | Full pipeline testable without any hardware |
| WebSocket ack/retry | Reliable command delivery |
| Docker ready | One command to spin up both services |

## Architecture

```
Camera → OpenCV (PC) → PID → WebSocket → RPi.GPIO → Motors
```

## Why Python 3.10+?

- Structural pattern matching (future use)
- Union types with `|` (clean type hints)
- Widely available on Raspberry Pi OS Bookworm

## Competition Relevance

DroneBot 2026 demonstrates:
- Sensor fusion (vision + pose markers)
- Real-time control loops
- Embedded Linux / GPIO programming
- Reliable networked communication

## Roadmap

- [ ] 3D depth camera integration (RealSense)
- [ ] Multi-fire source prioritisation
- [ ] Autonomous return-to-base after extinguishing
- [ ] ROS 2 integration
