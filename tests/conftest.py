from __future__ import annotations

import pytest

from tests._ontology_repo import RepoBuilder


@pytest.fixture
def ontology_repo(tmp_path) -> RepoBuilder:
    """A throw-away Git repository with a tracked RDF file."""
    return RepoBuilder(tmp_path / "repository")
