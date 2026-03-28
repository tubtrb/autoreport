"""Generation orchestration for report rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoreport.loader import load_yaml
from autoreport.models import ReportRequest
from autoreport.outputs.pptx_writer import PowerPointWriter
from autoreport.templates.weekly_report import (
    BASIC_TEMPLATE_NAME,
    SUPPORTED_TEMPLATE_NAMES,
    TEMPLATE_NAME,
    build_weekly_report_content_blocks,
    build_weekly_report_fill_plan,
    profile_basic_template,
    profile_weekly_template,
)
from autoreport.templates.autofill import (
    ContentBlock,
    DiagnosticReport,
    FillPlan,
    TemplateProfile,
)
from autoreport.validator import validate_report


@dataclass(slots=True)
class GenerationArtifacts:
    """Internal generation bundle used by the template-aware autofill flow."""

    template_profile: TemplateProfile
    content_blocks: list[ContentBlock]
    fill_plan: FillPlan
    diagnostic_report: DiagnosticReport


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

    writer = PowerPointWriter()
    presentation, effective_template_path = _prepare_presentation(
        writer,
        template_name=template_name,
        template_path=template_path,
    )
    artifacts = prepare_generation_artifacts_from_mapping(
        raw_data,
        presentation=presentation,
        template_path=effective_template_path,
        template_name=template_name,
    )
    return writer.write_fill_plan(
        presentation=presentation,
        output_path=output_path,
        fill_plan=artifacts.fill_plan,
    )


def prepare_generation_artifacts_from_mapping(
    raw_data: dict[str, Any],
    *,
    presentation,
    template_path: Path | None = None,
    template_name: str = TEMPLATE_NAME,
) -> GenerationArtifacts:
    """Build the template-aware autofill artifacts for one report generation."""

    report = validate_report(raw_data)
    if template_name == TEMPLATE_NAME:
        template_profile = profile_weekly_template(
            presentation,
            template_path=template_path,
        )
    elif template_name == BASIC_TEMPLATE_NAME:
        template_profile = profile_basic_template(
            presentation,
            template_path=template_path,
        )
    else:
        supported = ", ".join(SUPPORTED_TEMPLATE_NAMES)
        raise ValueError(
            f"Unsupported template: {template_name} "
            f"(supported: {supported})"
        )

    content_blocks = build_weekly_report_content_blocks(report)
    fill_plan, diagnostic_report = build_weekly_report_fill_plan(
        content_blocks,
        template_profile,
    )
    return GenerationArtifacts(
        template_profile=template_profile,
        content_blocks=content_blocks,
        fill_plan=fill_plan,
        diagnostic_report=diagnostic_report,
    )


def _prepare_presentation(
    writer: PowerPointWriter,
    *,
    template_name: str,
    template_path: Path | None,
):
    """Choose the runtime presentation source for a template profile."""

    if template_name != BASIC_TEMPLATE_NAME:
        return writer._load_presentation(template_path), template_path

    reference_presentation = (
        writer._load_presentation(template_path)
        if template_path is not None
        else None
    )
    presentation = writer._load_presentation(None)
    if reference_presentation is not None:
        presentation.slide_width = reference_presentation.slide_width
        presentation.slide_height = reference_presentation.slide_height
    return presentation, None

