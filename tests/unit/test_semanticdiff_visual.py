"""Unit tests for interactive visual graph export."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

from semanticdiff.render.visual import build_delta_data, render_diff_html

STATUS = "status"
ADDED = "added"
DELETED = "deleted"
UPDATED = "updated"


def _sample_graphs() -> tuple[Graph, Graph, URIRef, URIRef, URIRef]:
    base = Graph()
    later = Graph()

    s_updated = URIRef("http://example.org/Book")
    p_title = URIRef("http://example.org/title")
    base.add((s_updated, p_title, Literal("V1")))
    later.add((s_updated, p_title, Literal("V2")))

    s_added = URIRef("http://example.org/NewEntity")
    later.add((s_added, p_title, Literal("New")))

    s_deleted = URIRef("http://example.org/OldEntity")
    base.add((s_deleted, p_title, Literal("Old")))

    return base, later, s_added, s_deleted, s_updated


def test_build_delta_data_without_status() -> None:
    base, later, s_added, s_deleted, s_updated = _sample_graphs()

    nodes, edges = build_delta_data(base, later)
    node_statuses = {node["id"]: node[STATUS] for node in nodes}
    assert node_statuses[str(s_updated)] == UPDATED
    assert node_statuses[str(s_added)] == ADDED
    assert node_statuses[str(s_deleted)] == DELETED

    edge_statuses = {edge[STATUS] for edge in edges}
    assert edge_statuses == {ADDED, DELETED}


def test_build_delta_data_filters_by_status_added() -> None:
    base, later, s_added, s_deleted, _ = _sample_graphs()
    nodes, edges = build_delta_data(base, later, status=ADDED)
    assert all(edge[STATUS] == ADDED for edge in edges)
    assert any(node["id"] == str(s_added) for node in nodes)
    assert not any(node["id"] == str(s_deleted) for node in nodes)


def test_build_delta_data_filters_by_status_deleted() -> None:
    base, later, s_added, s_deleted, _ = _sample_graphs()
    nodes, edges = build_delta_data(base, later, status=DELETED)
    assert all(edge[STATUS] == DELETED for edge in edges)
    assert any(node["id"] == str(s_deleted) for node in nodes)
    assert not any(node["id"] == str(s_added) for node in nodes)


def test_build_delta_data_filters_by_status_updated() -> None:
    base, later, s_added, s_deleted, s_updated = _sample_graphs()
    nodes, _ = build_delta_data(base, later, status=UPDATED)
    up_node_ids = {node["id"] for node in nodes}
    assert str(s_updated) in up_node_ids
    assert str(s_added) not in up_node_ids
    assert str(s_deleted) not in up_node_ids


def test_build_delta_data_invalid_status() -> None:
    base, later, _, _, _ = _sample_graphs()
    with pytest.raises(ValueError, match="Unknown status"):
        build_delta_data(base, later, status="invalid")


def test_build_delta_data_node_formatting() -> None:
    base = Graph()
    later = Graph()

    bnode = BNode()
    pred = URIRef("http://example.org/pred#name")
    long_lit = Literal("This is a very long string that exceeds thirty characters")
    lang_lit = Literal("bonjour", lang="fr")
    typed_lit = Literal("42", datatype=XSD.integer)
    slash_uri = URIRef("http://example.org/path/resource")

    later.add((bnode, pred, long_lit))
    later.add((bnode, pred, lang_lit))
    later.add((bnode, pred, typed_lit))
    later.add((bnode, pred, slash_uri))

    nodes, edges = build_delta_data(base, later)
    assert len(nodes) > 0
    assert len(edges) == 4


def test_render_diff_html_cached_path(tmp_path: Path) -> None:
    base, later, _, _, _ = _sample_graphs()
    out_file = tmp_path / "diff.html"
    res1 = render_diff_html(base, later, out_file)
    assert res1 == out_file
    assert out_file.exists()

    out_file.write_text("already written", encoding="utf-8")
    res2 = render_diff_html(base, later, out_file)
    assert res2 == out_file
    assert out_file.read_text(encoding="utf-8") == "already written"
