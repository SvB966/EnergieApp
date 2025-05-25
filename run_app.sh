#!/usr/bin/env bash
set -euo pipefail

# ── Go to repo root ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Ensure logs dir exists ────────────────────────────────────────────────────
mkdir -p logs
if [[ ! -w logs ]]; then
  echo "[ERROR] Cannot write to logs/ – check volume mount or permissions." >&2
  exit 1
fi

# ── PYTHONPATH so helper modules & notebooks import properly ───────────────────
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/1. Notebooks:${PYTHONPATH:-}"

# ── Notebook ports ─────────────────────────────────────────────────────────────
UI_PORT="${PORT:-8868}"
NOTEBOOK_DIR="1. Notebooks"
declare -A NB_PORTS=(
  ["000_Start_UI.ipynb"]=$UI_PORT
  ["001_All_Types.ipynb"]=8866
  ["002_Data_export.ipynb"]=8867
  ["003_VMNED_Data_Export.ipynb"]=8869
  ["004_Factorupdate.ipynb"]=8870
  ["005_MV_Switch.ipynb"]=8871
  ["006_Vervanging_Tool.ipynb"]=8872
  ["007_Storage_Method.ipynb"]=8873
)

# ── Verify notebooks exist ────────────────────────────────────────────────────
for nb in "${!NB_PORTS[@]}"; do
  [[ -f "$NOTEBOOK_DIR/$nb" ]] \
    || { echo "[ERROR] Missing notebook: $NOTEBOOK_DIR/$nb" >&2; exit 1; }
done

# ── Launch Voila servers ──────────────────────────────────────────────────────
echo "[INFO] Launching Voila dashboards (using PATH from Dockerfile)…"
for nb in "${!NB_PORTS[@]}"; do
  port=${NB_PORTS[$nb]}
  if ! nc -z 127.0.0.1 "$port" 2>/dev/null; then
    echo "  → $NOTEBOOK_DIR/$nb → port $port"
    nohup voila "$NOTEBOOK_DIR/$nb" --port="$port" --no-browser --ip=0.0.0.0 \
      > "logs/${nb%.ipynb}.log" 2>&1 &
  else
    echo "  → port $port busy, skipping $nb"
  fi
done

# ── Wait for UI ────────────────────────────────────────────────────────────────
echo "[INFO] Waiting for UI at http://localhost:$UI_PORT …"
until nc -z 127.0.0.1 "$UI_PORT"; do sleep 2; done

echo "[INFO] EnergieApp live at http://localhost:$UI_PORT"
wait
