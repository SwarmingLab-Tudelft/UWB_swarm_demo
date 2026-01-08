# UWB Demo (uv-managed)

This project controls a Crazyflie swarm with a Tkinter GUI.

## Prerequisites
- Python 3.10+ installed.
- Install [uv](https://github.com/astral-sh/uv) (fast Python package manager):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## Setup
1. From the repository root run:
   ```bash
   uv sync
   ```
   This creates a local `.venv/` and installs dependencies from `pyproject.toml`.
2. (Optional) Activate the environment if you want a shell with the venv:
   ```bash
   source .venv/bin/activate
   ```

## Running
- Launch the GUI:
  ```bash
  uv run main.py
  ```

## Managing dependencies
- Add or bump a dependency (updates `pyproject.toml` and `uv.lock`):
  ```bash
  uv add PACKAGE_NAME
  ```
- Upgrade everything to latest allowed versions:
  ```bash
  uv lock --upgrade
  uv sync
  ```
- Remove a dependency:
  ```bash
  uv remove PACKAGE_NAME
  uv sync
  ```

## Notes
- Project metadata and dependencies live in `pyproject.toml`.
- uv will generate `uv.lock` on the first `uv sync` to lock versions.
- If `uv` is missing, install it via the command above or `sudo snap install astral-uv` on Ubuntu.
