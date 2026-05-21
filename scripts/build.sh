#!/usr/bin/env bash
set -euo pipefail

FUNCTION="${2:-}"

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
