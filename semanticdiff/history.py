"""Orchestration: pair every commit in a range with its semantic change set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from semanticdiff.changeset import compare
from semanticdiff.git_log import Commit, raw_diff, resolve, walk
from semanticdiff.loader import UnreadableRevisionError, graph_at_rev
from semanticdiff.vocabulary import ChangeSet


@dataclass(frozen=True)
class CommitChanges:
    """One commit and what it did to the vocabulary."""

    commit: Commit
    changes: ChangeSet
    unreadable: bool = False
    raw_text: str | None = None


def read_history(
    repo: Path,
    rev_range: str,
    path: str,
    *,
    with_text: bool = False,
    graphs: dict[str, Graph] | None = None,
) -> list[CommitChanges]:
    """Every commit in `rev_range` touching `path`, oldest first, with its changes.

    `graphs` memoises parsed revisions by revision name. Consecutive commits share
    one — the parent of each is the one before it — so walking N commits parses
    N+1 revisions rather than 2N, and a caller stepping through a history one
    commit at a time can hand the same dict back to keep what it already read.
    """
    memo: dict[str, Graph] = {} if graphs is None else graphs
    return [
        _entry(repo, commit, path, with_text=with_text, graphs=memo)
        for commit in walk(repo, rev_range, path)
    ]


def export_diff_html(
    repo: Path,
    path: str,
    sha: str,
    status: str | None = None,
    out_dir: Path | None = None,
    title: str | None = None,
) -> Path:
    from semanticdiff.render.visual import render_diff_html

    output_dir = out_dir or (repo / ".semanticdiff" / "diffs")
    filename = f"{sha}_{status}.html" if status else f"{sha}.html"
    out_path = output_dir / filename
    if out_path.exists():
        return out_path
    output_dir.mkdir(parents=True, exist_ok=True)
    base, later = _graphs_for_commit(repo, path, sha)
    suffix = f" [{status}]" if status else ""
    page_title = title or f"Commit {sha[:8]}{suffix}"
    return render_diff_html(base, later, out_path, title=page_title, status=status)


def _graphs_for_commit(
    repo: Path,
    path: str,
    sha: str,
    *,
    graphs: dict[str, Graph] | None = None,
) -> tuple[Graph, Graph]:
    """Return (parent_graph, child_graph) for a given commit sha."""
    memo: dict[str, Graph] = {} if graphs is None else graphs
    parent_g = _parent(repo, sha, path, memo)
    try:
        child_g = _at(repo, sha, path, memo)
    except UnreadableRevisionError:
        child_g = Graph()
    return parent_g, child_g


def _entry(
    repo: Path, commit: Commit, path: str, *, with_text: bool, graphs: dict[str, Graph]
) -> CommitChanges:
    try:
        later = _at(repo, commit.sha, path, graphs)
    except UnreadableRevisionError:
        # One bad revision must not end the walk — flag it and keep going.
        return CommitChanges(commit=commit, changes=ChangeSet(()), unreadable=True)
    return CommitChanges(
        commit=commit,
        changes=compare(_parent(repo, commit.sha, path, graphs), later),
        raw_text=raw_diff(repo, commit.sha, path) if with_text else None,
    )


def _at(repo: Path, rev: str, path: str, graphs: dict[str, Graph]) -> Graph:
    """The graph at `rev`, parsed once per *commit*, not once per name.

    Keyed on the resolved sha: `<sha>^` and the commit before it are the same
    revision under two names, and only resolving makes them share an entry.
    """
    key = resolve(repo, rev) or rev
    if key not in graphs:
        graphs[key] = graph_at_rev(repo, rev, path) or Graph()
    return graphs[key]


def _parent(repo: Path, sha: str, path: str, graphs: dict[str, Graph]) -> Graph:
    """The graph one commit earlier — empty at the first commit, or if it was broken."""
    try:
        return _at(repo, f"{sha}^", path, graphs)
    except UnreadableRevisionError:
        return Graph()
