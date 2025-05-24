#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# EnergieApp DASHBOARD LAUNCHER  –  POSIX-compliant, non-root friendly
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Jupyter writable dirs inside container’s layer (no /root) ────────────────
export XDG_DATA_HOME="$SCRIPT_DIR/.local/share"
export XDG_CONFIG_HOME="$SCRIPT_DIR/.config"
export XDG_RUNTIME_DIR="$SCRIPT_DIR/.runtime"
export HOME="$SCRIPT_DIR"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_RUNTIME_DIR" logs

# ── Configuration ────────────────────────────────────────────────────────────
UI_PORT="${PORT:-8868}"
NOTEBOOK_DIR="1. Notebooks"          # keep original Windows layout

declare -A NB_PORTS=(
  ["001_All_Types.ipynb"]=8866
  ["002_Data_export.ipynb"]=8867     # **case-exact** to repo file
  ["003_VMNED_Data_Export.ipynb"]=8869
  ["004_Factorupdate.ipynb"]=8870
  ["005_MV_Switch.ipynb"]=8871
  ["006_Vervanging_Tool.ipynb"]=8872
  ["007_Storage_Method.ipynb"]=8873
  ["000_Start_UI.ipynb"]=$UI_PORT
)

echo "[INFO] Verifying notebooks in '$NOTEBOOK_DIR'…"
declare -A PATH_PORT_MAP
for nb in "${!NB_PORTS[@]}"; do
  fullpath="$NOTEBOOK_DIR/$nb"
  [[ -f "$fullpath" ]] || { echo "[ERROR] $fullpath not found"; exit 1; }
  port=${NB_PORTS[$nb]}
  PATH_PORT_MAP["$fullpath"]=$port
done
echo "[INFO] All notebooks present."

echo "[INFO] Activating Conda env 'energieapp'…"
micromamba activate energieapp      # available in base image

echo "[INFO] Launching Voila instances…"
for path in "${!PATH_PORT_MAP[@]}"; do
  port=${PATH_PORT_MAP[$path]}
  if ! nc -z 127.0.0.1 "$port" 2>/dev/null; then
    echo "  → $path  →  $port"
    nohup voila "$path" --port="$port" --no-browser --ip=0.0.0.0 \
         > "logs/$(basename "${path%.ipynb}").log" 2>&1 &
  else
    echo "  → Port $port already in use, skipping $path"
  fi
done

echo "[INFO] Waiting for main UI on port $UI_PORT…"
until nc -z 127.0.0.1 "$UI_PORT"; do sleep 2; done
echo "[INFO] EnergieApp live at http://localhost:$UI_PORT"

# keep PID 1 alive
wait
