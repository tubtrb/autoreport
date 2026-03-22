"""Template helpers for weekly report slide generation.

The first production template will live here once the report schema and slide
mapping rules are finalized.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from autoreport.models import WeeklyReport


TEMPLATE_NAME = "weekly_report"


def build_weekly_report_context(report: WeeklyReport) -> dict[str, Any]:
    """Prepare template-friendly context from a loaded weekly report."""

    return dict(asdict(report))
