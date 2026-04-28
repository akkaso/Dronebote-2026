#!/usr/bin/env bash
# Esecuzione di esempio: avvia il server Pi mock, poi il client PC mock.
# Eseguire dalla radice del progetto: bash scripts/esecuzione_esempio.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Attiva il venv se presente
if [ -f ".venv-pc/bin/activate" ]; then
    source .venv-pc/bin/activate
fi

echo "=== Generazione video di esempio (se non presente) ==="
if [ ! -s sample_video.mp4 ]; then
    python3 scripts/genera_video_esempio.py
fi

echo "=== Avvio server Pi mock (in background) ==="
python3 pi/pi_ws_server.py --host 127.0.0.1 --port 8765 --mock &
PI_PID=$!
trap "kill $PI_PID 2>/dev/null || true" EXIT

# Attendi che il server sia pronto
sleep 1

echo "=== Avvio client PC mock ==="
python3 -m pc.vision_client \
    --source sample_video.mp4 \
    --ws ws://127.0.0.1:8765 \
    --no-display \
    --debug \
    --config pc/config.yaml

echo "=== Completato. ==="
