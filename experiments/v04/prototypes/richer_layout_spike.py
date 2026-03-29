"""Scaffold types for richer layout experiments.

The current v0.3 path focuses on template-aware autofill. This module is a
branch-local place to explore richer layout planning ideas without affecting the
existing writer or template contract.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LayoutExperimentCase:
    """A small description of a layout-planning scenario to evaluate."""

    slide_role: str
    content_blocks: list[str]
    slot_count: int


@dataclass(frozen=True)
class LayoutExperimentResult:
    """Minimal result shape for a layout-planning spike."""

    placements: list[str]
    warnings: list[str]


def describe_layout_gap(case: LayoutExperimentCase) -> str:
    """Return a human-readable summary for logging and design notes."""

    return (
        f"Role={case.slide_role}, blocks={len(case.content_blocks)}, "
        f"slots={case.slot_count}"
    )
