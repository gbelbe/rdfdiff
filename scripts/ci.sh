#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSIONS=("$@")
if [ "${#PYTHON_VERSIONS[@]}" -eq 0 ]; then
  PYTHON_VERSIONS=(3.12 3.13)
fi

for python in "${PYTHON_VERSIONS[@]}"; do
  uv sync --extra dev --python "$python"
  uv run --python "$python" ruff check .
  uv run --python "$python" ruff format --check .
  uv run --python "$python" mypy semanticdiff
  uv run --python "$python" pip-audit --skip-editable
  uv run --python "$python" pytest -q --cov=semanticdiff --cov-report=term-missing
done
