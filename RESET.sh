#!/usr/bin/env bash
# actions-lab reset — deterministic: down, keep/regenerate secrets, rebuild, health-gate.
set -euo pipefail
cd "$(dirname "$0")"

docker compose down -v --remove-orphans >/dev/null 2>&1 || true

# flags + runner token live in .env (never in git); generate on first run,
# keep them stable on every reset after that.
if [ ! -f .env ]; then
  sh gen-secrets.sh >/dev/null
  echo "RESET: no .env — generated fresh flags (see .env)" >&2
fi

docker compose up -d --build >/dev/null

# gate on both tiers being actually alive (no blind sleeps)
for i in $(seq 1 40); do
  if curl -fsS -o /dev/null http://127.0.0.1:18930/healthz 2>/dev/null \
     && curl -fsS -o /dev/null http://127.0.0.1:18931/healthz 2>/dev/null; then
    echo "RESET-OK portal http://127.0.0.1:18930 (queue http://127.0.0.1:18931)"
    exit 0
  fi
  sleep 2
done
echo "RESET-DEGRADED services not healthy after 80s — check: docker compose ps" >&2
exit 1
