#!/usr/bin/env bash
# test-and-deploy.sh — Run full test suite, then deploy landing page if clean.
# Usage: bash scripts/test-and-deploy.sh [--deploy]

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANDING_DIR="/home/ubuntu/workbench/graphbus-landing"
LOG="/tmp/pytest-full.log"

echo "=== GraphBus Test Suite ==="
cd "$REPO_ROOT"

# Run tests (redirect to file to avoid buffering issues)
python -m pytest tests/ -q --no-header --no-cov > "$LOG" 2>&1
EXIT=$?

# Show summary
tail -3 "$LOG"

if [ $EXIT -ne 0 ]; then
  echo ""
  echo "❌ Tests FAILED — aborting deploy."
  grep "FAILED\|ERROR" "$LOG" | head -20
  exit 1
fi

echo "✅ All tests passed."

# Deploy if requested
if [[ "$1" == "--deploy" ]]; then
  echo ""
  echo "=== Deploying Landing Page ==="
  cd "$LANDING_DIR"
  sudo docker build -t graphbus-landing:latest . -q
  sudo kind load docker-image graphbus-landing:latest --name graphbus 2>&1 | tail -1
  sudo kubectl rollout restart deployment/graphbus-landing
  sudo kubectl rollout status deployment/graphbus-landing --timeout=60s 2>&1 | tail -1
  echo "✅ Deployed."
fi
