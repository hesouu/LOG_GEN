#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/lambda/gold"
ZIP="${SRC}/gold-lambda.zip"

rm -f "${ZIP}"

(
  cd "${SRC}"
  zip -q "gold-lambda.zip" "main.py"
)

echo "[OK] ${ZIP}"