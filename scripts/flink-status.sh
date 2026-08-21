#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="${1:-ap-northeast-2}"
cd "$ROOT/infra"
APP_NAME="$(terraform output -raw flink_application_name)"
aws kinesisanalyticsv2 describe-application \
  --region "$REGION" \
  --application-name "$APP_NAME" \
  --query 'ApplicationDetail.{Name:ApplicationName,Status:ApplicationStatus,Runtime:RuntimeEnvironment}' \
  --output table
