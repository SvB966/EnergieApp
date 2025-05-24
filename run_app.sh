#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------
# EnergieApp launch script: starts all Voila dashboards
# -----------------------------------------------------------------

# Locate script dir and change into it
SCRIPT_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$SCRIPT_DIR"

# Main UI port (override via PORT)
UI_PORT="${PORT:-8868}"

# Directory containing notebooks
NOTEBOOK_DIR="1. Notebooks"

# Map notebook filenames to ports
declare -A NOTEBOOK_PORTS=(
  ["001_All_Types.ipynb"]=8866
  ["002_Data_Export.ipynb"]=8867
  ["003_VMNED_Data_Export.ipynb"]=8869
  ["004_Factorupdate.ipynb"]=8870
  ["005_MV_Switch.ipynb"]=8871
  ["006_Vervanging_Tool.ipynb"]=8872
  ["007_Storage_Method.ipynb"]=8873
  ["000_Start_UI.ipynb"]=${UI_PORT}
)

echo "[DEBUG] Checking required notebooks..."
# Verify each notebook exists and build full path->port map
for nb in "${!NOTEBOOK_PORTS[@]}"; do
  fullpath="$NOTEBOOK_DIR/$nb"
  port=${NOTEBOOK_PORTS[$nb]}
  if [[ ! -f "$fullpath" ]]; then
    echo "[ERROR] Notebook '$fullpath' not found"
    exit 1
  fi
  unset NOTEBOOK_PORTS[$nb]
  NOTEBOOK_PORTS["$fullpath"]=$port
done

echo "[INFO] All notebooks verified."

# Logs directory
mkdir -p logs

# Launch each Voila server (environment is already in PATH)
for path in "${!NOTEBOOK_PORTS[@]}"; do
  port=${NOTEBOOK_PORTS[$path]}
  name="$(basename "${path%.ipynb}")"
  logfile="logs/${name}.log"
  echo "[INFO] Launching Voila for '$path' on port $port"
  nohup voila "$path" --port="$port" --no-browser --ip="0.0.0.0" > "$logfile" 2>&1 &
done

# Wait for main UI
echo "[DEBUG] Waiting for main UI at http://localhost:${UI_PORT}..."
until nc -z 127.0.0.1 "$UI_PORT"; do
  sleep 2
done

echo "[INFO] Main UI is live at http://localhost:${UI_PORT}"

# Keep container alive
wait
