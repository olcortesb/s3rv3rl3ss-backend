#!/usr/bin/env bash
set -euo pipefail

FUNCTION="${2:-}"

# ECR login (needed only if use_container = true in samconfig.toml)
if grep -q "use_container = true" samconfig.toml 2>/dev/null; then
    echo "🔐 Logging into ECR Public..."
    aws ecr-public get-login-password --region us-east-1 | \
        docker login --username AWS --password-stdin public.ecr.aws
fi

# Build
if [[ -n "$FUNCTION" ]]; then
    echo "🔨 Building: $FUNCTION"
    sam build "$FUNCTION"
else
    echo "🔨 Building all..."
    sam build
fi

# Deploy
if [[ "${1:-}" == "deploy" ]]; then
    echo "🚀 Deploying..."
    sam deploy --config-file samconfig.local.toml
fi

echo "✅ Done"
