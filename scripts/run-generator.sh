#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-ecommerce}"
DURATION_SECONDS="${2:-300}"
BASE_RPS="${3:-2.0}"
CORRUPTION_RATE="${4:-0.03}"
TASK_COUNT="${5:-1}"
REGION="${6:-ap-northeast-2}"
TIME_SCALE="${7:-1.0}"

case "$DOMAIN" in ecommerce|finance|smartfactory|game) ;; *) echo "invalid domain" >&2; exit 1 ;; esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$ROOT/infra"
RUN_ID="loggen-$(date +%Y%m%d-%H%M%S)"

command -v jq >/dev/null 2>&1 || { echo "jq is required" >&2; exit 1; }

CLUSTER="$(terraform -chdir="$INFRA" output -raw ecs_cluster_name)"
TASK_DEFINITION="$(terraform -chdir="$INFRA" output -raw ecs_task_definition_arn)"
SECURITY_GROUP="$(terraform -chdir="$INFRA" output -raw security_group_id)"
SUBNET_CSV="$(terraform -chdir="$INFRA" output -json public_subnet_ids | jq -r 'join(",")')"

OVERRIDE_FILE="$(mktemp)"
jq -n \
  --arg domain "$DOMAIN" \
  --arg duration "$DURATION_SECONDS" \
  --arg rps "$BASE_RPS" \
  --arg scale "$TIME_SCALE" \
  --arg corruption "$CORRUPTION_RATE" \
  --arg runid "$RUN_ID" \
  '{containerOverrides:[{name:"log-generator",environment:[
    {name:"DOMAIN",value:$domain},
    {name:"DURATION_SECONDS",value:$duration},
    {name:"BASE_RPS",value:$rps},
    {name:"TIME_SCALE",value:$scale},
    {name:"CORRUPTION_RATE",value:$corruption},
    {name:"INCLUDE_CORRUPTION_LABEL",value:"false"},
    {name:"OUTPUT_MODE",value:"stdout"},
    {name:"RUN_ID",value:$runid}
  ]}]}' > "$OVERRIDE_FILE"

aws ecs run-task \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --launch-type FARGATE \
  --task-definition "$TASK_DEFINITION" \
  --count "$TASK_COUNT" \
  --started-by "$RUN_ID" \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_CSV],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --overrides "file://$OVERRIDE_FILE" \
  --query 'tasks[].taskArn' \
  --output table

rm -f "$OVERRIDE_FILE"
LOG_GROUP="$(terraform -chdir="$INFRA" output -raw cloudwatch_log_group)"
echo "Run ID: $RUN_ID"
echo "Follow logs: aws logs tail '$LOG_GROUP' --follow --region '$REGION'"
