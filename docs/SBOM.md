# Software Bill of Materials (SBOM) – DroneBot 2026

## PC (control node)

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| Python | ≥ 3.10 | PSF | Runtime |
| opencv-python | ≥ 4.9 | Apache 2.0 | Video capture, HSV thresholding, contour detection |
| opencv-contrib-python | ≥ 4.9 | Apache 2.0 | ArUco marker detection (`cv2.aruco`) |
| numpy | ≥ 1.26 | BSD-3-Clause | Array math for image processing |
| PyYAML | ≥ 6.0 | MIT | Configuration file parsing |
| pytest | ≥ 8.0 | MIT | Unit testing |

## Raspberry Pi (rover node)

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| Python | ≥ 3.10 | PSF | Runtime |
| RPi.GPIO | ≥ 0.7 | MIT | GPIO control for rover direction pins |

## Arduino (RC hack)

| Software | Version | License | Purpose |
|----------|---------|---------|---------|
| Arduino IDE | ≥ 2.3 | LGPL/GPL | Sketch compilation & upload |
| Arduino core (AVR) | ≥ 1.8 | LGPL | Microcontroller support |

No proprietary or cloud-based SDKs are used.  All packages listed above are
open-source and compilable from source code.

## Dependency installation

```bash
# PC
pip install opencv-python opencv-contrib-python numpy pyyaml pytest

# Raspberry Pi
pip install RPi.GPIO
```
