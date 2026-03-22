"""Shared data models used across loading, validation, and generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ReportRequest:
    """Represents a generation request received from the CLI layer."""

    source_path: Path
    output_path: Path | None = None
    template_name: str = "weekly_report"


@dataclass(slots=True)
class WeeklyReport:
    """Validated weekly report data used by downstream rendering layers."""

    title: str
    team: str
    week: str
    highlights: list[str]
    metrics: dict[str, int]
    risks: list[str]
    next_steps: list[str]
