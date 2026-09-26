from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from rdflib import Graph
from typer.testing import CliRunner

from semanticdiff import ChangeKind, compare, read_history
from semanticdiff.cli import app

PREFIXES = """\
@prefix ex: <https://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
"""


def graph(body: str) -> Graph:
    result = Graph()
    result.parse(data=PREFIXES + body, format="turtle")
    return result


def test_compare_reports_added_class_and_ignores_reformatting() -> None:
    before = graph('ex:Product a owl:Class ; rdfs:label "Product"@en .')
    reformatted = graph('ex:Product rdfs:label "Product"@en ; a owl:Class .')
    after = graph("ex:Product a owl:Class . ex:Vehicle a owl:Class .")

    assert len(compare(before, reformatted)) == 0
    changes = compare(before, after)
    vehicle = next(change for change in changes if change.curie == "ex:Vehicle")
    assert vehicle.kind is ChangeKind.ADDED


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True)
    for key, value in (("user.name", "Ada Lovelace"), ("user.email", "ada@example.test")):
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", key, value], check=True, capture_output=True
        )
    return tmp_path


def commit(repository: Path, text: str, message: str) -> None:
    (repository / "ontology.ttl").write_text(PREFIXES + text, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repository), "add", "ontology.ttl"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", message], check=True, capture_output=True
    )


def test_history_and_cli_report_semantic_changes(repository: Path) -> None:
    commit(repository, "ex:A a owl:Class .", "add A")
    commit(repository, "ex:A a owl:Class . ex:B a owl:Class .", "add B")

    history = read_history(repository, "HEAD", "ontology.ttl")
    result = CliRunner().invoke(app, ["log", "--repo", str(repository), "--file", "ontology.ttl"])

    assert [change.curie for change in history[-1].changes] == ["ex:B"]
    assert result.exit_code == 0
    assert "ex:B" in result.stdout
