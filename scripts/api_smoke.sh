#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ -f .venv/bin/activate ]]; then
    . .venv/bin/activate
fi

uvicorn telecom_twin.api:app --host 127.0.0.1 --port 8765 > /tmp/telecom-twin-api.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true' EXIT

for _ in {1..20}; do
    if curl --fail --silent http://127.0.0.1:8765/health > /tmp/telecom-twin-health.json; then
        break
    fi
    sleep 0.25
done

curl --fail --silent http://127.0.0.1:8765/health
printf '\n'
curl --fail --silent 'http://127.0.0.1:8765/telemetry/latest?node_id=access-07'
printf '\n'
curl --fail --silent -X POST 'http://127.0.0.1:8765/live/reset' > /tmp/telecom-twin-live-reset.json
curl --fail --silent -X POST 'http://127.0.0.1:8765/live/step?steps=125' \
    | python3 -c 'import json, sys; data=json.load(sys.stdin); assert data["timestamp_s"] == 124; print(data["anomaly_count"])'
curl --fail --silent -X POST 'http://127.0.0.1:8765/live/step?steps=176' > /tmp/telecom-twin-live-complete.json
curl --fail --silent 'http://127.0.0.1:8765/live/stream?interval_ms=20' \
    | grep --quiet '^data: '
curl --fail --silent http://127.0.0.1:8765/dashboard \
    | grep --quiet 'Telecom Network Digital Twin'
curl --fail --silent http://127.0.0.1:8765/experiments/multi-fault \
    | python3 -c 'import json, sys; assert len(json.load(sys.stdin)) == 12'
curl --fail --silent http://127.0.0.1:8765/openapi.json \
    | python3 -c 'import json, sys; print(sorted(json.load(sys.stdin)["paths"]))'
