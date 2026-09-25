# rdfdiff

`rdfdiff` reads an RDF file's Git history as changes to its vocabulary,
rather than as changed characters. It reports classes, properties, individuals,

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

```sh
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy semanticdiff
uv run pytest -q
```

The distribution is named `rdfdiff`; its Python import and command-line command
remain `semanticdiff`. The project deliberately has no dependency on Ster. Ster
can consume it as an optional integration, but the diff engine and command-line
tool remain usable with any RDF repository.

## Releases

Releases are published to PyPI by the `pypi-publish.yml` GitHub Actions workflow
when a `v*` tag is pushed. PyPI trusted publishing must be configured for the
`gbelbe/semanticdiff` repository, the `pypi-publish.yml` workflow, and the
  `pypi` environment before the first release tag is created. The pending PyPI
  publisher must use the `rdfdiff` project name.
