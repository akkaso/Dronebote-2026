#!/usr/bin/env bash
# Run the DroneBot 2026 Pi WebSocket server.
# Usage: bash pi/run_pi.sh [--host HOST] [--port PORT] [--mock]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Activate venv if present
if [ -f ".venv-pi/bin/activate" ]; then
    source .venv-pi/bin/activate
fi

python3 pi/pi_ws_server.py "$@"
