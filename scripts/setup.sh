#!/usr/bin/env bash
set -euo pipefail

REGION="${1:-ap-northeast-2}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$ROOT/infra"
GENERATOR="$ROOT/generator"

for cmd in aws terraform docker; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "$cmd is required" >&2; exit 1; }
done

echo "[1/4] Terraform init"
terraform -chdir="$INFRA" init

echo "[2/4] Terraform apply"
terraform -chdir="$INFRA" apply -auto-approve -var="aws_region=$REGION"

REPO="$(terraform -chdir="$INFRA" output -raw ecr_repository_url)"
REGISTRY="${REPO%%/*}"

echo "[3/4] ECR login"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo "[4/4] Build and push Python/Faker generator image"
docker build --no-cache --platform linux/amd64 -t "$REPO:latest" "$GENERATOR"
docker push "$REPO:latest"

echo "Setup complete"
echo "Example: ./scripts/run-generator.sh ecommerce 300 2.0 0.03"
