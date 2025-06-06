# Overview
This folder contains all Jupyter notebooks, shared Python modules and scripts used to launch the EnergieApp locally. The notebooks are rendered as Voila dashboards. Key files to edit include `202_launch_app.py`, `environment.yml`, `db_connection.py` and the various `*_utils.py` modules.

# Dev Environment Setup
```bash
conda env create -f environment.yml -n energymonitor_env
conda activate energymonitor_env
python verify_env_deps.py environment.yml energymonitor_env
# Start notebooks locally
python 202_launch_app.py
```

# Testing & Linting
- Automated tests are not provided yet. Add `pytest` cases under a `tests/` folder and run `pytest`.
- Run `ruff .` or `flake8 .` for linting once configured.

# Contribution Guidelines
- Follow PEP8 with 4-space indents.
- Keep environment dependencies in `environment.yml` in sync with imports.
- Document functions with docstrings and type hints.

# PR Instructions
- Use commit titles like `feat(notebooks): <summary>` or `fix(notebooks): <summary>`.
- PR titles should begin with `[Notebooks]` followed by a short description.
- Explain how to reproduce and test changes in the PR body.
