#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$ROOT/infra"

"$ROOT/scripts/build-flink.sh"

if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: Terraform이 필요합니다." >&2
  exit 1
fi

echo "[1/4] terraform init"
cd "$INFRA"
terraform init -upgrade

echo "[2/4] terraform fmt"
terraform fmt

echo "[3/4] terraform validate"
terraform validate

echo "[4/4] terraform apply"
terraform apply
