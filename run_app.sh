#!/usr/bin/env bash
set -euo pipefail

NOTEBOOK_DIR="/app/notebooks"
LOG_DIR="$NOTEBOOK_DIR/logs"
mkdir -p "$LOG_DIR"

declare -a APPS=(
  "001_All_Types.ipynb:8866"
  "002_Data_export.ipynb:8867"
  "003_VMNED_Data_Export.ipynb:8869"
  "004_Factorupdate.ipynb:8870"
  "005_MV_Switch.ipynb:8871"
  "006_Vervanging_Tool.ipynb:8872"
  "007_Storage_Method.ipynb:8873"
  "000_Start_UI.ipynb:8868"
)

for item in "${APPS[@]}"; do
  nb=${item%%:*}
  port=${item##*:}
  echo "Starting ${nb} on ${port}"
  voila "$NOTEBOOK_DIR/${nb}" --port="${port}" --no-browser --ip=0.0.0.0 \
    > "$LOG_DIR/${nb%.ipynb}.log" 2>&1 &
done

until curl -f http://localhost:8868 >/dev/null 2>&1; do
  sleep 1
done

echo "EnergieApp ready on port 8868"
tail -f "$LOG_DIR"/*.log
