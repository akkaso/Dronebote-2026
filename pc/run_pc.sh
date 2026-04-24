#!/usr/bin/env bash
# Run the DroneBot 2026 PC vision client.
# Usage: bash pc/run_pc.sh [OPTIONS]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Activate venv if present
if [ -f ".venv-pc/bin/activate" ]; then
    source .venv-pc/bin/activate
fi

python3 -m pc.vision_client "$@"
