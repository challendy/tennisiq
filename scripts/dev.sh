#!/usr/bin/env bash
# Start analysis + API locally (web is separate: cd web && pnpm dev)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export PATH="/usr/local/opt/postgresql@16/bin:$PATH"

echo "Starting analysis on :8090"
(
  cd "$ROOT/services/analysis"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec uvicorn app.main:app --host 127.0.0.1 --port 8090
) &
ANALYSIS_PID=$!

echo "Starting API on :5129"
(
  cd "$ROOT/src"
  exec dotnet run --project TennisIQ.Api --urls http://127.0.0.1:5129
) &
API_PID=$!

trap 'kill $ANALYSIS_PID $API_PID 2>/dev/null || true' EXIT
echo "analysis pid=$ANALYSIS_PID api pid=$API_PID"
echo "In another terminal: cd web && pnpm dev"
wait
