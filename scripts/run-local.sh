#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-ecommerce}"
DURATION_SECONDS="${2:-30}"
BASE_RPS="${3:-2.0}"
CORRUPTION_RATE="${4:-0.03}"
OUTPUT_MODE="${5:-both}"
TIME_SCALE="${6:-1.0}"

case "$DOMAIN" in ecommerce|finance|smartfactory|game) ;; *) echo "invalid domain" >&2; exit 1 ;; esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GENERATOR="$ROOT/generator"
mkdir -p "$ROOT/output"
LOG_FILE="$ROOT/output/${DOMAIN}-$(date +%Y%m%d-%H%M%S).jsonl"
RUN_ID="local-$(date +%Y%m%d-%H%M%S)"

export DOMAIN DURATION_SECONDS BASE_RPS CORRUPTION_RATE OUTPUT_MODE TIME_SCALE LOG_FILE RUN_ID
cd "$GENERATOR"
python -m app.main

echo "Generated log: $LOG_FILE"
