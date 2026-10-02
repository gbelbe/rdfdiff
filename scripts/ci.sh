#!/usr/bin/env bash
set -euo pipefail

FAST=0
FRESH=0
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --fresh) FRESH=1 ;;
    *) ARGS+=("$arg") ;;
  esac
done

# Tidy First ratchet — diff-aware (needs a base to compare against), so run
# once, directly, not per Python version. Text-only check on commit messages,
# no test run — milliseconds. See the tidy-first skill for the catalog.
if [[ $FAST -eq 0 ]] && git rev-parse --verify --quiet origin/main >/dev/null; then
  bash scripts/check_tidy_ratchet.sh --base origin/main
else
  echo "⚠ origin/main not found — skipping tidy ratchet (run: git fetch origin main)" >&2
fi

PYTHON_VERSIONS=("${ARGS[@]}")
if [ "${#PYTHON_VERSIONS[@]}" -eq 0 ]; then
PYTHON_VERSIONS=(3.12 3.13)
fi

last_python=""
for python in "${ARGS[@]:-${PYTHON_VERSIONS[@]}}"; do
  uv sync --extra dev --python "$python"
  uv run --python "$python" ruff check .
  uv run --python "$python" ruff format --check .
  uv run --python "$python" mypy semanticdiff
  uv run --python "$python" pip-audit --skip-editable
  uv run --python "$python" pytest -q --cov=semanticdiff --cov-report=term-missing --cov-report=xml
  last_python="$python"
done

if [[ $FAST -eq 0 ]]; then
  if [[ $FRESH -eq 1 ]]; then
    rm -rf mutants
  fi
  uv run --python "$last_python" mutmut run
  uv run --python "$last_python" python scripts/check_mutation_ratchet.py --base origin/main --threshold 80
fi

uv run --python "$last_python" python scripts/craftcov_pr_comment.py --base origin/main --dry-run > craftcov-report.md
uv run --python "$last_python" python scripts/craftcov.py --format sarif --no-cache --no-diff > craftcov.sarif

# Patch coverage — diff-aware like the tidy ratchet above, so once, not per
# Python version (coverage.xml above is from whichever version ran last in
# the loop; its content doesn't depend on which one produced it). Reuses
# that file rather than a second pytest run just to get a second XML.
# ${arr[-1]} would do this more directly but needs bash 4.3+; macOS ships
# 3.2 as /usr/bin/bash, so this script tracks the last value by hand.
if [[ $FAST -eq 0 ]] && git rev-parse --verify --quiet origin/main >/dev/null; then
  uv run --python "$last_python" diff-cover coverage.xml --compare-branch origin/main --fail-under 90
else
  echo "⚠ origin/main not found — skipping patch coverage (run: git fetch origin main)" >&2
fi
