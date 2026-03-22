"""Generation orchestration for report rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from autoreport.loader import load_yaml
from autoreport.models import ReportRequest
from autoreport.outputs.pptx_writer import PowerPointWriter
from autoreport.templates.weekly_report import (
    TEMPLATE_NAME,
    build_weekly_report_context,
)
from autoreport.validator import validate_report


def generate_report(request: ReportRequest) -> Path:
    """Generate a report artifact from a structured request."""

    output_path = request.output_path or Path("output") / (
        f"{request.source_path.stem}.pptx"
    )
    raw_data = load_yaml(request.source_path)
    return generate_report_from_mapping(
        raw_data,
        output_path=output_path,
        template_path=request.template_path,
        template_name=request.template_name,
    )


def generate_report_from_mapping(
    raw_data: dict[str, Any],
    *,
    output_path: Path,
    template_path: Path | None = None,
    template_name: str = TEMPLATE_NAME,
) -> Path:
    """Generate a report artifact from an already-parsed mapping."""

    if template_name != TEMPLATE_NAME:
        raise ValueError(f"Unsupported template: {template_name}")

    report = validate_report(raw_data)
    context = build_weekly_report_context(report)

    writer = PowerPointWriter()
    return writer.write(
        template_path=template_path,
        output_path=output_path,
        context=context,
    )

