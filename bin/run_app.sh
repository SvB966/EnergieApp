#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# EnergieApp DASHBOARD LAUNCHER – POSIX-compliant, works in WSL or Docker
###############################################################################
# 1) Loads the micromamba shell hook so `micromamba activate` works in scripts
# 2) Activates env `energieapp`
# 3) Starts every Voila notebook (000–007) on its own port
# 4) Waits until the main UI (000_Start_UI.ipynb) is live on $UI_PORT
###############################################################################

# ---------------------------------------------------------------------------
# Initialise micromamba for this subshell
# ---------------------------------------------------------------------------
eval "$(micromamba shell hook --shell bash)"

# ---------------------------------------------------------------------------
# Resolve repository root and switch there
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Ensure Jupyter writes cache & logs inside the repo, even when running
# as an unprivileged user in Docker.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Ensure Jupyter writes cache & logs inside the repo
# ---------------------------------------------------------------------------
ORIG_HOME="${HOME}"                      # <── added
export XDG_DATA_HOME="$SCRIPT_DIR/.local/share"
export XDG_CONFIG_HOME="$SCRIPT_DIR/.config"
export XDG_RUNTIME_DIR="$SCRIPT_DIR/.runtime"
export HOME="$SCRIPT_DIR"
export MAMBA_ROOT_PREFIX="${ORIG_HOME}/.local/share/mamba"   # <── added
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_RUNTIME_DIR" logs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UI_PORT="${PORT:-8868}"               # main dashboard port (can override with PORT=XXXX)
NOTEBOOK_DIR="1. Notebooks"           # keep original folder layout

declare -A NB_PORTS=(
  ["001_All_Types.ipynb"]=8866
  ["002_Data_export.ipynb"]=8867      # **case-exact** filename
  ["003_VMNED_Data_Export.ipynb"]=8869
  ["004_Factorupdate.ipynb"]=8870
  ["005_MV_Switch.ipynb"]=8871
  ["006_Vervanging_Tool.ipynb"]=8872
  ["007_Storage_Method.ipynb"]=8873
  ["000_Start_UI.ipynb"]=$UI_PORT
)

# ---------------------------------------------------------------------------
# Verify notebooks exist
# ---------------------------------------------------------------------------
echo "[INFO] Verifying notebooks in '$NOTEBOOK_DIR'…"
declare -A PATH_PORT_MAP
for nb in "${!NB_PORTS[@]}"; do
  fullpath="$NOTEBOOK_DIR/$nb"
  [[ -f "$fullpath" ]] || { echo "[ERROR] $fullpath not found"; exit 1; }
  PATH_PORT_MAP["$fullpath"]=${NB_PORTS[$nb]}
done
echo "[INFO] All notebooks present."

# ---------------------------------------------------------------------------
# Activate Conda environment
# ---------------------------------------------------------------------------
echo "[INFO] Activating Conda env 'energieapp'…"
micromamba activate energieapp

# ---------------------------------------------------------------------------
# Launch Voila instances
# ---------------------------------------------------------------------------
echo "[INFO] Launching Voila servers…"
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

# ---------------------------------------------------------------------------
# Wait until the main dashboard is reachable
# ---------------------------------------------------------------------------
echo "[INFO] Waiting for main UI at http://localhost:$UI_PORT …"
until nc -z 127.0.0.1 "$UI_PORT"; do sleep 2; done
echo "[INFO] EnergieApp is live at http://localhost:$UI_PORT"

# Keep the script’s PID (PID 1 in a container) alive
wait
