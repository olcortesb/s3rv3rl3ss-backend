#!/usr/bin/env bash
set -euo pipefail

echo "🔐 Logging into ECR Public..."
aws ecr-public get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin public.ecr.aws

echo "🔨 Running sam build..."
sam build

if [[ "${1:-}" == "deploy" ]]; then
  echo "🚀 Deploying..."
  sam deploy --config-file samconfig.local.toml
fi

echo "✅ Done"
