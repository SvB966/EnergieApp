#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# EnergieApp DASHBOARD LAUNCHER – POSIX‐compliant (WSL, Docker, bare metal)
###############################################################################

# ---------------------------------------------------------------------------
# Micromamba shell‐hook (enables `micromamba activate` in scripts)
# ---------------------------------------------------------------------------
eval "$(micromamba shell hook --shell bash)"

# ---------------------------------------------------------------------------
# Repository root (script sits in the repo root)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Jupyter + micromamba writable dirs (non‐root safe)
# ---------------------------------------------------------------------------
ORIG_HOME="${HOME}"
export XDG_DATA_HOME="$SCRIPT_DIR/.local/share"
export XDG_CONFIG_HOME="$SCRIPT_DIR/.config"
export XDG_RUNTIME_DIR="$SCRIPT_DIR/.runtime"
export HOME="$SCRIPT_DIR"
export MAMBA_ROOT_PREFIX="${ORIG_HOME}/.local/share/mamba"
mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_RUNTIME_DIR" logs

# ---------------------------------------------------------------------------
# Make Python see the helper modules co‐located with the notebooks
# ---------------------------------------------------------------------------
export PYTHONPATH="$SCRIPT_DIR/1. Notebooks:${PYTHONPATH:-}"

# ---------------------------------------------------------------------------
# Notebook ports configuration
# ---------------------------------------------------------------------------
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

echo "[INFO] Verifying notebooks in '$NOTEBOOK_DIR'…"
declare -A PATH_PORT_MAP
for nb in "${!NB_PORTS[@]}"; do
  full="$NOTEBOOK_DIR/$nb"
  [[ -f "$full" ]] || { echo "[ERROR] $full not found"; exit 1; }
  PATH_PORT_MAP["$full"]=${NB_PORTS[$nb]}
done
echo "[INFO] All notebooks present."

# ---------------------------------------------------------------------------
# Activate the Conda environment
# ---------------------------------------------------------------------------
echo "[INFO] Activating Conda env 'energieapp'…"
micromamba activate energieapp

# ---------------------------------------------------------------------------
# Launch each Voila server in the background
# ---------------------------------------------------------------------------
echo "[INFO] Launching Voila servers…"
for path in "${!PATH_PORT_MAP[@]}"; do
  port=${PATH_PORT_MAP[$path]}
  if ! nc -z 127.0.0.1 "$port" 2>/dev/null; then
    echo "  → $path → $port"
    nohup voila "$path" --port="$port" --no-browser --ip=0.0.0.0 \
      > "logs/$(basename "${path%.ipynb}").log" 2>&1 &
  else
    echo "  → Port $port busy, skipping $path"
  fi
done

# ---------------------------------------------------------------------------
# Wait until the main UI is reachable
# ---------------------------------------------------------------------------
echo "[INFO] Waiting for main UI at http://localhost:$UI_PORT …"
until nc -z 127.0.0.1 "$UI_PORT"; do sleep 2; done
echo "[INFO] EnergieApp live at http://localhost:$UI_PORT"

# Keep this process alive (especially in Docker)
wait
