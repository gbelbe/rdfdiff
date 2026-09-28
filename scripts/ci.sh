#!/usr/bin/env bash
set -euo pipefail

# Tidy First ratchet — diff-aware (needs a base to compare against), so run
# once, directly, not per Python version. Text-only check on commit messages,
# no test run — milliseconds. See the tidy-first skill for the catalog.
if git rev-parse --verify --quiet origin/main >/dev/null; then
  bash scripts/check_tidy_ratchet.sh --base origin/main
else
  echo "⚠ origin/main not found — skipping tidy ratchet (run: git fetch origin main)" >&2
fi

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
