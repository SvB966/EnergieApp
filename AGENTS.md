# EnergieApp Repository Guide

This project contains two main source folders:

- **1. Notebooks** – Jupyter notebooks and helper Python modules.
- **2. Stored Procedures** – SQL Server procedures used by the notebooks.

Each directory has its own `AGENTS.md` with build and deployment commands:

- [1. Notebooks/AGENTS.md](1. Notebooks/AGENTS.md)
- [2. Stored Procedures/AGENTS.md](2. Stored Procedures/AGENTS.md)

The notebooks expect a Conda environment defined in `1. Notebooks/environment.yml`.
Deployment typically involves launching the notebooks with Voila and loading the SQL
procedures into your database.
