#!/usr/bin/env bash
# Avvia il server WebSocket Pi di DroneBot 2026.
# Utilizzo: bash pi/avvia_pi.sh [--host HOST] [--port PORT] [--mock]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Attiva il venv se presente
if [ -f ".venv-pi/bin/activate" ]; then
    source .venv-pi/bin/activate
fi

python3 pi/pi_ws_server.py "$@"
