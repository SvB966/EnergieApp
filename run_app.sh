#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/1. Notebooks"

declare -a notebooks=(
  "001_All_Types.ipynb 8866"
  "002_Data_export.ipynb 8867"
  "003_VMNED_Data_Export.ipynb 8869"
  "004_Factorupdate.ipynb 8870"
  "005_MV_Switch.ipynb 8871"
  "006_Vervanging_Tool.ipynb 8872"
  "007_Storage_Method.ipynb 8873"
  "000_Start_UI.ipynb 8868"
)

pids=()
for item in "${notebooks[@]}"; do
  nb="$(echo "$item" | awk '{print $1}')"
  port="$(echo "$item" | awk '{print $2}')"
  echo "[INFO] Launching $nb on port $port"
  voila "$nb" --port="$port" --no-browser --ip=0.0.0.0 &
  pids+=("$!")
  sleep 0.5
done

while ! nc -z localhost 8868; do
  sleep 2
done

trap 'echo "[INFO] Shutting down"; kill "${pids[@]}"' SIGINT SIGTERM

wait -n
