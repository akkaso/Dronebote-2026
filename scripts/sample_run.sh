#!/usr/bin/env bash
# Sample run: start Pi mock server, then PC mock client.
# Run from the project root: bash scripts/sample_run.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Activate venv if present
if [ -f ".venv-pc/bin/activate" ]; then
    source .venv-pc/bin/activate
fi

echo "=== Generating sample video if not present ==="
if [ ! -s sample_video.mp4 ]; then
    python3 scripts/generate_sample_video.py
fi

echo "=== Starting Pi mock server (background) ==="
python3 pi/pi_ws_server.py --host 127.0.0.1 --port 8765 --mock &
PI_PID=$!
trap "kill $PI_PID 2>/dev/null || true" EXIT

# Wait for server to be ready
sleep 1

echo "=== Starting PC mock client ==="
python3 -m pc.vision_client \
    --source sample_video.mp4 \
    --ws ws://127.0.0.1:8765 \
    --no-display \
    --debug \
    --config pc/config.yaml

echo "=== Done. ==="
