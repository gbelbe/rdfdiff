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

last_python=""
for python in "${PYTHON_VERSIONS[@]}"; do
  uv sync --extra dev --python "$python"
  uv run --python "$python" ruff check .
  uv run --python "$python" ruff format --check .
  uv run --python "$python" mypy semanticdiff
  uv run --python "$python" pip-audit --skip-editable
  uv run --python "$python" pytest -q --cov=semanticdiff --cov-report=term-missing --cov-report=xml
  last_python="$python"
done

# Patch coverage — diff-aware like the tidy ratchet above, so once, not per
# Python version (coverage.xml above is from whichever version ran last in
# the loop; its content doesn't depend on which one produced it). Reuses
# that file rather than a second pytest run just to get a second XML.
# ${arr[-1]} would do this more directly but needs bash 4.3+; macOS ships
# 3.2 as /usr/bin/bash, so this script tracks the last value by hand.
if git rev-parse --verify --quiet origin/main >/dev/null; then
  uv run --python "$last_python" diff-cover coverage.xml --compare-branch origin/main --fail-under 90
else
  echo "⚠ origin/main not found — skipping patch coverage (run: git fetch origin main)" >&2
fi
