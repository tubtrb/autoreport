"""Scaffold types for v0.4 text-shaping experiments.

These types are intentionally branch-local and are not imported by the current
runtime. They provide a stable place to try interface ideas before deciding
whether any text-shaping capability belongs in the product path.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TextShapingInput:
    """Minimal input for experimenting with summary and bullet shaping."""

    section_title: str
    bullets: list[str]
    audience: str = "internal"


@dataclass(frozen=True)
class TextShapingResult:
    """Prototype result shape for text-shaping experiments."""

    headline: str
    bullets: list[str]
    warnings: list[str]


class TextShaper(Protocol):
    """Protocol for a prototype text-shaping implementation."""

    def shape(self, payload: TextShapingInput) -> TextShapingResult:
        """Return a shaped headline and bullet set for the given payload."""


def not_implemented_text_shaper(_payload: TextShapingInput) -> TextShapingResult:
    """Explicit placeholder until a real v0.4 spike exists."""

    raise NotImplementedError(
        "v0.4 text-shaping experiments are scaffolded but not implemented."
    )
