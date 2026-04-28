#!/usr/bin/env bash
# Avvia il client di visione PC di DroneBot 2026.
# Utilizzo: bash pc/avvia_pc.sh [OPZIONI]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Attiva il venv se presente
if [ -f ".venv-pc/bin/activate" ]; then
    source .venv-pc/bin/activate
fi

python3 -m pc.vision_client "$@"
