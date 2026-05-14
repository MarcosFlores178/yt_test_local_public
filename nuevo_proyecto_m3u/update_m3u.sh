#!/bin/bash

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="${1:-config.json}"

python3 generate.py --config "$CONFIG_FILE"
python3 revive.py --config "$CONFIG_FILE"

echo "$(date): Proceso de generación y revive completado." >> run.log
