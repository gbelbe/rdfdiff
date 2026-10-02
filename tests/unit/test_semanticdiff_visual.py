"""Unit tests for interactive visual graph export."""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef

from semanticdiff.render.visual import build_delta_data

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
