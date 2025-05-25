#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v docker >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "[ERROR] Docker Compose not found." >&2; exit 1
fi

"${COMPOSE[@]}" up --build -d
echo "[INFO] EnergieApp running at http://localhost:8868"

# open browser
if [[ "$(uname)" == "Darwin" ]]; then open http://localhost:8868
elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8868; fi
