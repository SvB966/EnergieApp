#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$APP_DIR"
ENV_NAME="energieapp"
UI_PORT=8868
declare -A NOTEBOOK_PORTS=(
  [001_All_Types.ipynb]=8866
  [002_Data_export.ipynb]=8867
  [003_VMNED_Data_Export.ipynb]=8869
  [004_Factorupdate.ipynb]=8870
  [005_MV_Switch.ipynb]=8871
  [006_Vervanging_Tool.ipynb]=8872
  [007_Storage_Method.ipynb]=8873
  [000_Start_UI.ipynb]=$UI_PORT
)
echo "[DEBUG] Checking notebooks..."
for nb in "${!NOTEBOOK_PORTS[@]}"; do
  [[ -f "$nb" ]] || { echo "[ERROR] Missing $nb"; exit 1; }
done
echo "[DEBUG] Activating $ENV_NAME..."
micromamba activate "$ENV_NAME"
echo "[INFO] Launching Voila..."
mkdir -p logs
for nb in "${!NOTEBOOK_PORTS[@]}"; do
  port=${NOTEBOOK_PORTS[$nb]}
  name="${nb%.ipynb}"
  nohup voila "$nb" --port="$port" --no-browser --ip="0.0.0.0" \
    > "logs/${name}.log" 2>&1 &
done
echo "[DEBUG] Waiting for UI..."
while ! nc -z localhost $UI_PORT; do sleep 2; done
echo "[INFO] UI up at http://localhost:$UI_PORT"
wait
