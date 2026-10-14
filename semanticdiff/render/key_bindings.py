"""Key bindings for visual diff navigation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from semanticdiff.render.visual import _STATUS_ADDED, _STATUS_DELETED, _STATUS_UPDATED


def make_visual_diff_bindings(
    action: Callable[..., Any],
) -> tuple[tuple[str, str, str], ...]:
    """Key bindings targeting caller's chosen action method."""
    action_name = action.__name__.removeprefix("action_")
    return (
        ("h", action_name, "HTML diff"),
        ("a", f"{action_name}('{_STATUS_ADDED}')", "Added"),
        ("d", f"{action_name}('{_STATUS_DELETED}')", "Deleted"),
        ("u", f"{action_name}('{_STATUS_UPDATED}')", "Updated"),
    )


__all__ = [
    "make_visual_diff_bindings",
]
