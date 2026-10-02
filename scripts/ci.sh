#!/usr/bin/env bash
# Local CI for semanticdiff. Run this before every push.
set -euo pipefail

SENTINEL=".ci-passed"
rm -f "$SENTINEL"
FAST=0
FIX=0
FRESH=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --fix) FIX=1 ;;
    --fresh) FRESH=1 ;;
  esac
done

if [[ $FIX -eq 1 ]]; then
  uvx prek run --all-files || true
  uvx prek run --all-files
else
  SKIP=complexity-ratchet uvx prek run --all-files
fi

if git rev-parse --verify --quiet origin/main >/dev/null; then
  bash scripts/check_tidy_ratchet.sh --base origin/main
  uv run python scripts/check_complexity_ratchet.py --path semanticdiff --base origin/main
else
  echo "origin/main not found — skipping diff-aware gates (run: git fetch origin main)" >&2
fi

uv sync --extra dev
uv run pip-audit --skip-editable
if [[ $FAST -eq 1 ]]; then
  uv run pytest -q --tb=short
else
  uv run pytest -q --tb=short --cov=semanticdiff --cov-report=term-missing --cov-report=xml
fi

if [[ $FAST -eq 0 ]]; then
  if [[ $FRESH -eq 1 ]]; then
    rm -rf mutants
  fi
  uv run mutmut run
  uv run python scripts/check_mutation_ratchet.py --base origin/main --threshold 80
  if git rev-parse --verify --quiet origin/main >/dev/null; then
    uv run diff-cover coverage.xml --compare-branch origin/main --fail-under 90
  fi
fi

uv run python scripts/craftcov_pr_comment.py --base origin/main --dry-run > craftcov-report.md
uv run python scripts/craftcov.py --format sarif --no-cache --no-diff > craftcov.sarif

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$SENTINEL"
