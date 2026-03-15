"""Generation orchestration for report rendering.

This module will eventually coordinate loading, validation, template
preparation, and output writing.
"""

from __future__ import annotations

from pathlib import Path

from autoreport.models import ReportRequest


def generate_report(request: ReportRequest) -> Path:
    """Generate a report artifact from a structured request."""

    raise NotImplementedError(
        "Report generation orchestration is not implemented yet."
    )

