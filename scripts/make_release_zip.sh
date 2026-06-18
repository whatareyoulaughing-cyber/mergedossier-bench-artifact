#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-/tmp/MergeDossier-Bench-release.zip}"
cd "$ROOT/.."
zip -r "$OUT" "$(basename "$ROOT")" -x '*/.venv/*' '*/__pycache__/*' '*/.pytest_cache/*' '*/data/private/*' '*/data/raw/*'
echo "$OUT"
