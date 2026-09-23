#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
. .venv/bin/activate
ruff check .
pytest -q
telecom-twin experiment --output-dir /tmp/telecom-twin-verification
telecom-twin benchmark --output-dir /tmp/telecom-twin-benchmark --trials-per-root 2
telecom-twin online-evaluation --output-dir /tmp/telecom-twin-online
telecom-twin multi-fault-benchmark --output-dir /tmp/telecom-twin-multifault --trials-per-scenario 2
telecom-twin demo-gif --output /tmp/telecom-twin-demo.gif
scripts/api_smoke.sh
