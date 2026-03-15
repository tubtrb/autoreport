"""Generation orchestration for report rendering."""

from __future__ import annotations

from pathlib import Path

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

    if request.template_name != TEMPLATE_NAME:
        raise ValueError(f"Unsupported template: {request.template_name}")

    raw_data = load_yaml(request.source_path)
    report = validate_report(raw_data)
    context = build_weekly_report_context(report)

    output_path = request.output_path or Path("output") / (
        f"{request.source_path.stem}.pptx"
    )

    writer = PowerPointWriter()
    return writer.write(
        template_path=request.template_path,
        output_path=output_path,
        context=context,
    )

