#!/usr/bin/env bash
# Local CI — the same checks GitHub Actions runs, driven by prek. Run this
# before every push; it must be fully green before shipping.
#
# Static checks run via prek (.pre-commit-config.yaml) — the exact hooks the
# GitHub `test` job runs. Tests run on the current Python only locally (fast
# feedback); GitHub Actions runs the 3.12 / 3.13 matrix on every PR.
#
# Usage:
#   scripts/ci.sh            # full gate: prek + pip-audit + tests + diff-cover
#   scripts/ci.sh --fast     # skip the patch-coverage gate (quick dev check)
#   scripts/ci.sh --fix      # let prek's hooks auto-fix, then re-run to verify
#
# Modelled on ster's own scripts/ci.sh (same repo family) — scaled down: no
# import-linter (one flat package, nothing to enforce a boundary on), no JS.

set -euo pipefail

SENTINEL=".ci-passed"
rm -f "$SENTINEL"

FAST=0
FIX=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --fix)  FIX=1  ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
PASS="${GREEN}✓${NC}"; FAIL="${RED}✗${NC}"

step() { printf "\n${CYAN}── %s ──${NC}\n" "$1"; }
ok()   { printf "${PASS} %s\n" "$1"; }

step "Install deps"
uv sync --extra dev
ok "deps synced ($(uv run python --version))"

step "Static checks (prek run --all-files)"
if [[ $FIX -eq 1 ]]; then
  uvx prek run --all-files || true
  uvx prek run --all-files
else
  SKIP=complexity-ratchet uvx prek run --all-files
fi
ok "prek"

# The ratchet is diff-aware and needs --base, which prek has no way to supply
# (see .pre-commit-config.yaml) — run it directly against origin/main, the
# same ref CI compares a PR's base against.
step "Complexity ratchet — no function may grow worse past 15"
if git rev-parse --verify --quiet origin/main >/dev/null; then
  uv run python scripts/check_complexity_ratchet.py --path semanticdiff --base origin/main
  ok "complexity ratchet"
else
  echo "origin/main not found — skipping (run: git fetch origin main)"
fi

step "Security (pip-audit)"
uv run pip-audit --skip-editable
ok "pip-audit"

step "Tests (current Python $(uv run python --version | awk '{print $2}'))"
if [[ $FAST -eq 1 ]]; then
  uv run pytest -q --tb=short
  ok "pytest (fast, no coverage)"
else
  uv run pytest -q --tb=short --cov=semanticdiff --cov-report=term-missing --cov-report=xml
  ok "pytest"
fi

# ── Patch coverage gate (diff-cover vs origin/main) — full mode only ─────────
if [[ $FAST -eq 0 ]]; then
  step "Patch coverage (diff-cover vs origin/main)"
  if git rev-parse --verify --quiet origin/main >/dev/null; then
    uv run diff-cover coverage.xml --compare-branch origin/main --fail-under 90
    ok "patch coverage ≥ 90%"
  else
    echo "origin/main not found — skipping patch coverage (run: git fetch origin main)"
  fi
fi

touch "$SENTINEL"
printf "\n${GREEN}══════════════════════════════════════════\n  All checks passed — ready to push  ✓\n══════════════════════════════════════════${NC}\n"
