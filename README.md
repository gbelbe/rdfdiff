# rdfdiff

[![checks](https://github.com/gbelbe/rdfdiff/actions/workflows/ci.yml/badge.svg)](https://github.com/gbelbe/rdfdiff/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rdfdiff.svg)](https://pypi.org/project/rdfdiff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

`rdfdiff` reads an RDF file's Git history as changes to its vocabulary,
rather than as changed characters. It reports classes, properties, individuals,
concepts and ontologies as added, removed, modified, renamed, or deprecated.

Equivalent RDF serializations produce no semantic change, so reformatting,
prefix changes, reordered triples, and blank-node relabeling do not hide actual
ontology evolution.

## Install

```sh
uv tool install rdfdiff
```

Or run the current checkout:

```sh
uv run semanticdiff log --repo /path/to/ontology-repository
```

## Use

Summarize every commit that changed an RDF file:

```sh
semanticdiff log v0.1..v0.2 --repo /path/to/ontology-repository --file ontology.ttl
```

Trace one entity through a revision range:

```sh
semanticdiff show ex:Product v0.1..HEAD --repo /path/to/ontology-repository --file ontology.ttl
```

When a repository has exactly one tracked RDF file, `--file` is optional. Use
`--text` with `log` to append Git's raw hunks after the semantic report.

## Library API

```python
from rdflib import Graph
from semanticdiff import compare

changes = compare(before_graph, after_graph)
```

`read_history(repo, revision_range, path)` pairs each commit touching `path`
with its semantic change set. The public vocabulary is exported from the package
root: `Change`, `ChangeKind`, `ChangeSet`, `CommitChanges`, and `EntityKind`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the branch/commit conventions,
and the full local development workflow. Quick start:

```sh
uv sync --extra dev
bash scripts/install-hooks.sh   # one-time: pre-commit + pre-push hooks
bash scripts/ci.sh              # full local gate before every push
```

`scripts/ci.sh` runs on your current interpreter (fast feedback); GitHub
Actions runs the full 3.12 / 3.13 matrix on every PR. Pass `--fast` to skip
the patch-coverage gate during iteration, or `--fix` to let the linters
auto-fix what they can before re-checking.

The distribution is named `rdfdiff`; its Python import and command-line command
remain `semanticdiff`. The project deliberately has no dependency on Ster. Ster
can consume it as an optional integration, but the diff engine and command-line
tool remain usable with any RDF repository.

The test suite includes pure graph comparisons, Git-history and CLI tests, and
BDD scenarios for semantic change reporting. The throw-away Git repositories in
the tests exercise real Git plumbing rather than mocks.

## Releases

Releases are published to PyPI by the `pypi-publish.yml` GitHub Actions workflow
when a `v*` tag is pushed. PyPI trusted publishing must be configured for the
`gbelbe/rdfdiff` repository, the `pypi-publish.yml` workflow, and the `pypi`
environment before the first release tag is created. The pending PyPI publisher
must use the `rdfdiff` project name.

**Known gap:** trusted publishing was not configured before `v0.1.1` was
tagged, so that publish failed (`invalid-publisher`) and only `0.1.0` is
live on PyPI today. Configure the trusted publisher on
[PyPI's project settings](https://pypi.org/manage/project/rdfdiff/settings/publishing/)
before pushing another release tag.
