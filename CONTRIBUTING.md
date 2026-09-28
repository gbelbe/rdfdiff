# Contributing to rdfdiff

Thank you for considering a contribution. This guide walks you through the
process from first clone to merged pull request.

---

## 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12 – 3.13 | [python.org](https://www.python.org/downloads/) |
| uv | latest | `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | 2.x+ | system package manager |

To run both Python versions in the test matrix you need both interpreters
installed. `uv` can manage them for you:

```bash
uv python install 3.12 3.13
```

---

## 2. Clone and set up

```bash
git clone https://github.com/gbelbe/rdfdiff.git
cd rdfdiff

# Install all dependencies (runtime deps are core; dev adds the test/lint tools)
uv sync --extra dev

# Install the git pre-commit / pre-push hooks (one-time, per clone)
bash scripts/install-hooks.sh
```

The pre-push hook ensures you cannot accidentally push code that has not
passed the local CI gate (see step 4).

---

## 3. Create a branch

Always work on a feature branch, never directly on `main`:

```bash
git checkout -b feat/my-feature
```

Use a short, descriptive prefix:

| Prefix | Use for |
|--------|---------|
| `feat/` | new feature |
| `fix/` | bug fix |
| `refactor/` | internal restructure with no behaviour change |
| `docs/` | documentation only |
| `chore/` | tooling, CI, dependencies |

---

## 4. Develop and test locally

### Run the full CI gate (required before pushing)

```bash
bash scripts/ci.sh
```

The static checks are driven by **prek** (`.pre-commit-config.yaml`) — the *same
hooks* the git pre-commit hook and the GitHub `checks` job run, so local and CI
can't drift:

| Step | Driven by |
|------|-----------|
| Lint · format · types · security · hygiene · complexity ratchet | `prek run --all-files` — ruff (incl. its `S`/flake8-bandit SAST rules) · ruff-format · mypy · `scripts/check_complexity_ratchet.py` |
| CVE scan | `pip-audit --skip-editable` |
| Tests + coverage | `pytest --cov=semanticdiff` — **current Python only, locally** (fast feedback) |
| Patch coverage (≥ 90%) | `diff-cover` vs `origin/main` |

Tests run on your current interpreter locally; **GitHub Actions runs the
3.12 / 3.13 matrix on every PR** — so support for both is enforced on the PR,
not locally. After pushing, check `gh pr checks` to confirm every version is
green.

On success `scripts/ci.sh` writes a `.ci-passed` sentinel. The pre-push hook
reads it and blocks `git push` if the gate has not passed in the last 60
minutes.

### Faster iteration during development

```bash
bash scripts/ci.sh --fast   # current Python, skips the patch-coverage gate
bash scripts/ci.sh --fix    # let prek auto-fix ruff lint/format, then re-run the gate
```

### Run a specific test file

```bash
uv run pytest tests/unit/test_semanticdiff_changeset.py -v
```

### Auto-fix lint and format

```bash
uv run ruff check --fix .
uv run ruff format .
```

---

## 5. Commit

Write clear, focused commits. One logical change per commit.

```
<type>(<scope>): <short summary>

Optional longer explanation if the why is non-obvious.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.

---

## 6. Open a pull request

Push your branch and open a PR against `main`:

```bash
git push -u origin feat/my-feature
```

The pre-push hook will block the push if `bash scripts/ci.sh` has not been
run and passed within the last 60 minutes. If blocked, run CI first:

```bash
bash scripts/ci.sh
git push -u origin feat/my-feature
```

Then open the PR on GitHub. In the description:

- Explain **what** changed and **why**
- Reference any related issues (`Closes #123`)
- List any manual testing steps you performed

---

## 7. What happens next

- GitHub Actions runs the same CI pipeline on your branch automatically
- A maintainer reviews the code
- Address review comments with new commits (do not force-push during review)
- Once approved and CI is green, the PR is merged

---

## Coding conventions

1. **Clarify & simplify first** — restate the request, ask the questions that
   change the design, and apply **YAGNI** to cut scope to the simplest thing
   that works.
2. **Test-first / BDD** — write the Gherkin `.feature` (`tests/features/`) and
   unit tests (`tests/unit/`) before the implementation. Changed lines must be
   ≥ 90% covered *(enforced by `diff-cover`)*.
3. **Bug fixes** — add a regression test that fails before the fix, plus the
   related edge cases. A fix with no test is incomplete.
4. **Refactor on touch** — when a change would add complexity, refactor instead
   of piling on branches. A touched function already over the threshold must
   come *down*, never up *(enforced by the complexity ratchet, threshold 15)*.
   Update the affected tests.
5. **Dependencies** — keep them minimal (YAGNI: today just `rdflib` and
   `typer`), constrain versions, and commit `uv.lock`. This project
   deliberately has no dependency on `ster` — it stays usable against any RDF
   repository, and `ster` consumes it as an optional integration, never the
   other way round.
6. **Hygiene** — don't suppress linter/type errors with `# noqa` / `# type:
   ignore` unless it's a confirmed false positive (say why inline); comments
   explain the **why**, not the **what**.
7. **Preserve the public surface** — the distribution is named `rdfdiff`, but
   its Python import and CLI command remain `semanticdiff` on purpose (so
   existing integrations, including `ster`'s, don't need a rename alongside a
   packaging change). Don't casually rename the import.

All of the above run via `bash scripts/ci.sh` and GitHub Actions.

---

## Troubleshooting

**`git push` is blocked even after CI passes**

The sentinel expires after 60 minutes. Re-run `bash scripts/ci.sh`.

**Hook not installed on a fresh clone**

Run `bash scripts/install-hooks.sh` once after cloning.

**A Python version is missing from the test matrix**

```bash
uv python install 3.12   # or 3.13
bash scripts/ci.sh
```

**`pip-audit` reports a CVE**

Upgrade the affected package first:

```bash
uv lock --upgrade-package <package-name>
bash scripts/ci.sh
```

---

## Releasing a new version (maintainers)

There is no release-automation script yet (see ster's `scripts/release.sh` for
the shape one could take). Today, releasing is manual:

1. Bump `version` in `pyproject.toml`.
2. Run `bash scripts/ci.sh` and confirm it's green.
3. Commit, tag `vX.Y.Z`, and push both: `git push origin main --tags`.
4. The `pypi-publish.yml` workflow builds and publishes on the tag push —
   **provided PyPI trusted publishing is configured** for this repository,
   the `pypi-publish.yml` workflow, and the `pypi` environment (see the
   README's Releases section). If it isn't yet, the publish job fails with
   `invalid-publisher` and the tag is not undone automatically — fix the
   trusted-publisher config on PyPI, then push a new patch tag.
