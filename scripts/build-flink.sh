#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLINK_DIR="$ROOT/flink"

if ! command -v mvn >/dev/null 2>&1; then
  echo "ERROR: Maven(mvn)이 필요합니다. JDK 11 + Maven을 설치한 뒤 다시 실행하세요." >&2
  exit 1
fi

echo "[1/2] Build PyFlink application package"
cd "$FLINK_DIR"
mvn clean package

ARTIFACT="$FLINK_DIR/target/flink-silver.zip"
if [[ ! -f "$ARTIFACT" ]]; then
  echo "ERROR: Flink 배포 ZIP이 생성되지 않았습니다: $ARTIFACT" >&2
  exit 1
fi

echo "[2/2] Build complete"
echo "$ARTIFACT"
