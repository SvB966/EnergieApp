#!/usr/bin/env bash
# ------------------------------------------------------------------
# refactor_layout.sh – one-shot repo tidy-up for EnergieApp
# ------------------------------------------------------------------
# * Moves helper modules out of “1. Notebooks/” into a proper
#   package  energieapp/
# * Normalises the case of 002_Data_export.ipynb
# * Removes stale __pycache__ folders
# * Creates skeleton assets/ and __init__.py
#
# Run from the repository root (where environment.yml lives).
# Commit with a new branch so Git history stays clear.
# ------------------------------------------------------------------

set -euo pipefail

[[ -f environment.yml ]] || {
  echo "[ERROR] Run this script from the repo root (environment.yml missing)." >&2
  exit 1
}

echo "→ Creating package directory  energieapp/"
mkdir -p energieapp

echo "→ Moving helper modules into energieapp/ ..."
for f in caching.py common_imports.py db_connection.py \
         frequency_utils.py mappings.py progress_bar_widget.py
do
  src="1. Notebooks/$f"
  if [[ -f "$src" ]]; then
    # use git mv if repo is under Git to preserve history
    git mv "$src" energieapp/ 2>/dev/null || mv "$src" energieapp/
  fi
done

echo "→ Adding __init__.py (if absent)"
touch energieapp/__init__.py

echo "→ Removing __pycache__ artefacts inside 1. Notebooks/"
find "1. Notebooks" -type d -name '__pycache__' -exec rm -rf {} +

echo "→ Ensuring 1. Notebooks/assets/ exists"
mkdir -p "1. Notebooks/assets"

echo "→ Normalising filename case for 002 notebook (Linux case-sensitivity)"
old="1. Notebooks/002_Data_Export.ipynb"
new="1. Notebooks/002_Data_export.ipynb"
if [[ -f "$old" && ! -f "$new" ]]; then
  # two-step rename handles case-only changes on some filesystems
  git mv "$old" "${old}.tmp" 2>/dev/null || mv "$old" "${old}.tmp"
  git mv "${old}.tmp" "$new" 2>/dev/null || mv "${old}.tmp" "$new"
fi

echo "→ DONE. Review with: git status"
