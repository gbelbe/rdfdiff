"""Unit tests for visual diff key bindings factory."""

from __future__ import annotations

from semanticdiff import make_visual_diff_bindings
from semanticdiff.render.key_bindings import (
    make_visual_diff_bindings as direct_make,
)

EXPECTED_BINDING_COUNT = 4
EXPECTED_BINDING_WIDTH = 3


def test_make_visual_diff_bindings_from_callable() -> None:
    def action_open_visual_diff(self: object) -> None:
        pass

    bindings = make_visual_diff_bindings(action_open_visual_diff)
    assert len(bindings) == EXPECTED_BINDING_COUNT
    assert all(len(binding) == EXPECTED_BINDING_WIDTH for binding in bindings)
    keys = [b[0] for b in bindings]
    assert keys == ["h", "a", "d", "u"]
    actions = [b[1] for b in bindings]
    expected = [
        "open_visual_diff",
        "open_visual_diff('added')",
        "open_visual_diff('deleted')",
        "open_visual_diff('updated')",
    ]
    assert actions == expected
    assert direct_make(action_open_visual_diff) == bindings
