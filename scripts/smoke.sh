#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

(
  cd services/analysis
  .venv/bin/python - <<'PY'
from pathlib import Path
from app.pose.estimator import write_blank_video
path = Path("/tmp/tennisiq-smoke.mp4")
write_blank_video(path, frame_count=45)
print(f"wrote {path} ({path.stat().st_size} bytes)")
PY
)

EMAIL="chris+smoke$(date +%s)@tennisiq.local"
echo "Registering $EMAIL"
REG=$(curl -sS -X POST http://127.0.0.1:5129/api/auth/register \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"password123\",\"displayName\":\"Chris Smoke\",\"handedness\":\"right\"}")
echo "$REG"
TOKEN=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])' <<<"$REG")

echo "Uploading…"
UP=$(curl -sS -X POST http://127.0.0.1:5129/api/videos \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/tennisiq-smoke.mp4;type=video/mp4" \
  -F "stroke=forehand")
echo "$UP"
JOB=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["jobId"])' <<<"$UP")

JOBR=""
for i in $(seq 1 60); do
  JOBR=$(curl -sS "http://127.0.0.1:5129/api/jobs/$JOB" -H "Authorization: Bearer $TOKEN")
  STATUS=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$JOBR")
  echo "poll $i status=$STATUS"
  if [[ "$STATUS" == "Succeeded" || "$STATUS" == "Failed" ]]; then
    echo "$JOBR"
    break
  fi
  sleep 2
done

AID=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("analysisId") or "")' <<<"$JOBR")
[[ -n "$AID" ]] || { echo "No analysisId"; exit 1; }

echo "Analysis:"
curl -sS "http://127.0.0.1:5129/api/analyses/$AID" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -80

echo "Practice plan:"
curl -sS -X POST "http://127.0.0.1:5129/api/practice/plans?analysisId=$AID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -40

echo "Progress:"
curl -sS http://127.0.0.1:5129/api/progress -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -40

echo "SMOKE OK"
