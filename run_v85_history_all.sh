#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for avd in {1..8}; do
  echo "Kör historik for avdelning ${avd}..."
  python3 "${SCRIPT_DIR}/get_v85_history.py" --avd "${avd}"
done
