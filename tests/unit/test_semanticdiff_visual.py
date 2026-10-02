"""Unit tests for interactive visual graph export."""

from __future__ import annotations

from rdflib import Graph, Literal, URIRef

from semanticdiff.render.visual import build_delta_data


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
    node_ids = {node["id"] for node in nodes}
    assert str(s_updated) in node_ids
    assert str(s_added) in node_ids
    assert str(s_deleted) in node_ids

    s_node = next(node for node in nodes if node["id"] == str(s_updated))
    assert s_node["status"] == "updated"
    added_node = next(node for node in nodes if node["id"] == str(s_added))
    assert added_node["status"] == "added"
    deleted_node = next(node for node in nodes if node["id"] == str(s_deleted))
    assert deleted_node["status"] == "deleted"

    statuses = {edge["status"] for edge in edges}
    assert "added" in statuses
    assert "deleted" in statuses


def test_build_delta_data_filters_by_status_added() -> None:
    base, later, s_added, s_deleted, _ = _sample_graphs()
    nodes, edges = build_delta_data(base, later, status="added")
    assert all(edge["status"] == "added" for edge in edges)
    assert any(node["id"] == str(s_added) for node in nodes)
    assert not any(node["id"] == str(s_deleted) for node in nodes)


def test_build_delta_data_filters_by_status_deleted() -> None:
    base, later, s_added, s_deleted, _ = _sample_graphs()
    nodes, edges = build_delta_data(base, later, status="deleted")
    assert all(edge["status"] == "deleted" for edge in edges)
    assert any(node["id"] == str(s_deleted) for node in nodes)
    assert not any(node["id"] == str(s_added) for node in nodes)


def test_build_delta_data_filters_by_status_updated() -> None:
    base, later, s_added, s_deleted, s_updated = _sample_graphs()
    nodes, _ = build_delta_data(base, later, status="updated")
    up_node_ids = {node["id"] for node in nodes}
    assert str(s_updated) in up_node_ids
    assert str(s_added) not in up_node_ids
    assert str(s_deleted) not in up_node_ids
