"""Unit tests for the terminal renderers — the layers of the drill-down."""

from __future__ import annotations

from semanticdiff.git_log import Commit
from semanticdiff.history import CommitChanges
from semanticdiff.render.text import render_commits, render_entity, render_summary
from semanticdiff.vocabulary import Change, ChangeKind, ChangeSet, EntityKind

RANGE = "v0.1..v0.2"
VEHICLE = "ex:Vehicle"
PRODUCT = "ex:Product"


def commit(subject: str = "add a class", sha: str = "1085c9c0", other_files: int = 0) -> Commit:
    return Commit(
        sha=sha,
        short_sha=sha[:7],
        author="Ada Lovelace",
        date="2026-09-04T10:00:00+02:00",
        subject=subject,
        other_files=other_files,
    )


def change(
    kind: ChangeKind = ChangeKind.ADDED,
    curie: str = VEHICLE,
    label: str | None = None,
    detail: tuple[str, ...] = (),
    previous_curie: str | None = None,
    entity: EntityKind = EntityKind.CLASS,
    of_class: str | None = None,
) -> Change:
    return Change(
        kind=kind,
        entity=entity,
        uri=f"http://example.org/{curie.split(':')[-1]}",
        curie=curie,
        label=label,
        label_lang="en" if label else None,
        previous_curie=previous_curie,
        detail=detail,
        of_class=of_class,
    )


def individuals(n: int, of_class: str, kind: ChangeKind = ChangeKind.ADDED, start: int = 0):
    """`n` individual changes of one class, as a bulk edit would produce."""
    return [
        change(kind, f"ex:n{i}", entity=EntityKind.INDIVIDUAL, of_class=of_class)
        for i in range(start, start + n)
    ]


def entry(*changes: Change, subject: str = "add a class", other_files: int = 0) -> CommitChanges:
    return CommitChanges(
        commit=commit(subject=subject, other_files=other_files),
        changes=ChangeSet(changes),
    )


# ── layer 0: the summary ──────────────────────────────────────────────────────


def describe_summary():
    def it_counts_by_change_kind() -> None:
        history = [
            entry(change(ChangeKind.ADDED, "ex:A"), change(ChangeKind.ADDED, "ex:B")),
            entry(change(ChangeKind.MODIFIED, "ex:C"), change(ChangeKind.REMOVED, "ex:D")),
        ]

        out = render_summary(history, RANGE)

        assert "2 added" in out
        assert "1 modified" in out
        assert "1 removed" in out

    def it_omits_kinds_with_zero_count() -> None:
        out = render_summary([entry(change(ChangeKind.ADDED, "ex:A"))], RANGE)

        assert "removed" not in out
        assert "renamed" not in out

    def it_names_the_revision_range_and_commit_count() -> None:
        history = [entry(change(), subject="one"), entry(change(curie="ex:B"), subject="two")]

        out = render_summary(history, RANGE)

        assert RANGE in out
        assert "2 commits" in out

    def it_reports_when_history_is_empty() -> None:
        assert "no commits" in render_summary([], RANGE).lower()


# ── layer 1: the per-commit view ──────────────────────────────────────────────


def describe_commit_view():
    def it_names_added_entity() -> None:
        out = render_commits([entry(change(ChangeKind.ADDED, VEHICLE))])

        assert VEHICLE in out
        assert "1085c9c" in out
        assert "Ada Lovelace" in out

    def it_prefers_label_over_uri() -> None:
        out = render_commits([entry(change(ChangeKind.ADDED, VEHICLE, label="Vehicle"))])

        assert "Vehicle" in out
        assert VEHICLE in out

    def it_falls_back_to_curie_when_unlabelled() -> None:
        assert VEHICLE in render_commits([entry(change(ChangeKind.ADDED, VEHICLE, label=None))])

    def it_shows_change_detail() -> None:
        out = render_commits(
            [entry(change(ChangeKind.MODIFIED, PRODUCT, detail=("+2 properties",)))]
        )

        assert "+2 properties" in out

    def it_shows_a_rename_with_both_uris() -> None:
        renamed = change(ChangeKind.RENAMED, "ex:Store", previous_curie="ex:Shop")

        out = render_commits([entry(renamed)])

        assert "ex:Shop" in out
        assert "ex:Store" in out

    def it_notes_non_rdf_files_changed() -> None:
        assert "2 non-RDF files" in render_commits([entry(change(), other_files=2)])

    def it_omits_the_non_rdf_note_when_there_are_none() -> None:
        assert "non-RDF" not in render_commits([entry(change(), other_files=0)])

    def it_reports_commit_with_no_semantic_change() -> None:
        out = render_commits([entry(subject="reformat only")])

        assert "reformat only" in out
        assert "no semantic change" in out.lower()

    def it_detects_pure_formatting() -> None:
        """The file changed and the graph did not — say which, not just "nothing"."""
        assert "pure formatting" in render_commits([entry(subject="reformat only")]).lower()

    def it_flags_unreadable_commit() -> None:
        broken = CommitChanges(
            commit=commit(subject="broken"), changes=ChangeSet(()), unreadable=True
        )

        assert "unreadable" in render_commits([broken]).lower()

    def it_renders_no_commits_message_for_empty_history() -> None:
        assert "no commits" in render_commits([]).lower()

    def describe_raw_text():
        def _with_raw_text() -> CommitChanges:
            return CommitChanges(
                commit=commit(),
                changes=ChangeSet((change(),)),
                raw_text="diff --git a/onto.ttl b/onto.ttl\n+ex:Vehicle a owl:Class .",
            )

        def it_omits_text_by_default() -> None:
            assert "diff --git" not in render_commits([_with_raw_text()])

        def it_includes_raw_hunk_when_text_option_is_true() -> None:
            assert "diff --git" in render_commits([_with_raw_text()], show_text=True)


# ── layer 2: one entity's story ───────────────────────────────────────────────


def describe_entity_view():
    def it_filters_to_one_uri() -> None:
        history = [
            entry(change(ChangeKind.ADDED, PRODUCT), subject="one"),
            entry(change(ChangeKind.ADDED, "ex:Van"), subject="two"),
            entry(change(ChangeKind.MODIFIED, PRODUCT), subject="three"),
        ]

        out = render_entity(history, PRODUCT)

        assert "one" in out
        assert "three" in out
        assert "two" not in out

    def it_accepts_a_full_uri() -> None:
        history = [entry(change(ChangeKind.ADDED, PRODUCT), subject="one")]

        assert "one" in render_entity(history, "http://example.org/Product")

    def it_reports_when_entity_never_changed() -> None:
        out = render_entity([entry(change(ChangeKind.ADDED, PRODUCT))], "ex:Absent")

        assert "ex:Absent" in out
        assert "never changed" in out.lower()


# ── bulk individuals are counted, not listed ──────────────────────────────────


def describe_individual_tallying():
    def it_tallies_bulk_individual_additions_per_class() -> None:
        out = render_commits([entry(*individuals(1203, "City"))])

        assert "1203 individuals" in out
        assert "ex:n0" not in out

    def it_names_the_class_in_the_tally() -> None:
        assert "(City)" in render_commits([entry(*individuals(20, "City"))])

    def it_tallies_individuals_of_different_classes_separately() -> None:
        out = render_commits(
            [entry(*individuals(20, "City"), *individuals(30, "Store", start=100))]
        )

        assert "20 individuals" in out
        assert "30 individuals" in out

    def it_tallies_added_and_removed_individuals_separately() -> None:
        out = render_commits(
            [
                entry(
                    *individuals(20, "City"),
                    *individuals(9, "City", kind=ChangeKind.REMOVED, start=100),
                )
            ]
        )

        assert "+20 individuals" in out
        assert "-9 individuals" in out

    def it_lists_a_few_individuals_rather_than_tallying() -> None:
        """Three names say more than the number three."""
        out = render_commits([entry(*individuals(3, "City"))])

        assert "ex:n0" in out
        assert "3 individuals" not in out

    def it_evaluates_threshold_per_class_not_per_commit() -> None:
        out = render_commits([entry(*individuals(2, "City"), *individuals(2, "Store", start=100))])

        assert "individuals" not in out
        assert "ex:n0" in out and "ex:n100" in out

    def it_lists_renamed_individual_even_when_siblings_are_tallied() -> None:
        renamed = change(
            ChangeKind.RENAMED,
            "ex:region-sibiu",
            previous_curie="ex:city-sibiu",
            entity=EntityKind.INDIVIDUAL,
            of_class="City",
        )
        out = render_commits([entry(*individuals(50, "City"), renamed)])

        assert "ex:city-sibiu" in out
        assert "ex:region-sibiu" in out
        assert "50 individuals" in out

    def it_lists_deprecated_individual_even_when_siblings_are_tallied() -> None:
        gone = change(
            ChangeKind.DEPRECATED, "ex:old", entity=EntityKind.INDIVIDUAL, of_class="City"
        )
        out = render_commits([entry(*individuals(50, "City"), gone)])

        assert "ex:old" in out

    def it_never_tallies_classes_and_properties() -> None:
        many = [change(ChangeKind.ADDED, f"ex:C{i}") for i in range(30)]

        out = render_commits([entry(*many)])

        assert "ex:C0" in out
        assert "30 " not in out

    def it_tallies_individuals_with_no_class_together() -> None:
        out = render_commits([entry(*individuals(20, None))])

        assert "20 individuals" in out

    def it_still_lists_class_changes_in_a_tallied_commit() -> None:
        out = render_commits(
            [
                entry(
                    change(ChangeKind.MODIFIED, PRODUCT, detail=("+2 properties",)),
                    *individuals(50, "City"),
                )
            ]
        )

        assert PRODUCT in out
        assert "+2 properties" in out
        assert "50 individuals" in out


# ── interactive visual graph export ───────────────────────────────────────────


def describe_visual_graph():
    def it_builds_delta_data_and_exports_diff_html(tmp_path) -> None:
        from rdflib import Graph, Literal, URIRef

        from semanticdiff.render.visual import (
            build_delta_data,
            render_diff_html,
        )

        base = Graph()
        later = Graph()

        s = URIRef("http://example.org/Product")
        p = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
        o1 = Literal("Old Product")
        o2 = Literal("New Product")

        base.add((s, p, o1))
        later.add((s, p, o2))

        nodes, edges = build_delta_data(base, later)
        node_ids = {n["id"] for n in nodes}
        assert str(s) in node_ids
        assert str(o1) in node_ids
        assert str(o2) in node_ids

        # s is in both added and removed triples -> updated
        s_node = next(n for n in nodes if n["id"] == str(s))
        assert s_node["status"] == "updated"
        o1_node = next(n for n in nodes if n["id"] == str(o1))
        assert o1_node["status"] == "deleted"
        o2_node = next(n for n in nodes if n["id"] == str(o2))
        assert o2_node["status"] == "added"

        assert len(edges) == 2
        statuses = {e["status"] for e in edges}
        assert "added" in statuses
        assert "deleted" in statuses

        out_file = tmp_path / "diff.html"
        res = render_diff_html(base, later, out_file, title="Test Diff")
        assert res == out_file
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "<title>" not in content or "Test Diff" in content
        assert "Test Diff" in content
        assert "vis.Network" in content

        # Second call returns existing file directly without recalculation or overwrite
        out_file.write_text("existing content", encoding="utf-8")
        res2 = render_diff_html(base, later, out_file, title="New Title")
        assert res2 == out_file
        assert out_file.read_text(encoding="utf-8") == "existing content"

    def describe_status_filter():
        def it_filters_by_status() -> None:
            from rdflib import Graph, Literal, URIRef

            from semanticdiff.render.visual import build_delta_data

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

            # Filter added
            nodes_add, edges_add = build_delta_data(base, later, status="added")
            assert all(e["status"] == "added" for e in edges_add)
            assert any(n["id"] == str(s_added) for n in nodes_add)
            assert not any(n["id"] == str(s_deleted) for n in nodes_add)

            # Filter deleted
            nodes_del, edges_del = build_delta_data(base, later, status="deleted")
            assert all(e["status"] == "deleted" for e in edges_del)
            assert any(n["id"] == str(s_deleted) for n in nodes_del)
            assert not any(n["id"] == str(s_added) for n in nodes_del)

            # Filter updated
            nodes_up, edges_up = build_delta_data(base, later, status="updated")
            up_node_ids = {n["id"] for n in nodes_up}
            assert str(s_updated) in up_node_ids
            assert str(s_added) not in up_node_ids
            assert str(s_deleted) not in up_node_ids
