#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/build-flink.sh"
cd "$ROOT/infra"
terraform init -upgrade
terraform fmt
terraform validate
terraform apply -var="flink_start_application=true"
