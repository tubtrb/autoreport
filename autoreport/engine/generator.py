"""Generation orchestration for contract-first Autoreport rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoreport.loader import load_yaml
from autoreport.models import ReportRequest, ReportPayload, TemplateContract
from autoreport.outputs.pptx_writer import PowerPointWriter
from autoreport.template_flow import (
    PUBLIC_BUILT_IN_TEMPLATE_NAME,
    get_built_in_contract,
    get_built_in_profile,
)
from autoreport.templates.autofill import (
    DiagnosticReport,
    FillPlan,
    PlannedTextFill,
    TemplateProfile,
)
from autoreport.templates.weekly_report import (
    build_report_fill_plan,
    export_template_contract,
    profile_template,
)
from autoreport.validator import validate_payload


@dataclass(slots=True)
class GenerationArtifacts:
    """Internal generation bundle used by the contract-first flow."""

    template_profile: TemplateProfile
    template_contract: TemplateContract
    report_payload: ReportPayload
    fill_plan: FillPlan
    diagnostic_report: DiagnosticReport
    generation_summary: "GenerationSummary"


@dataclass(slots=True)
class GenerationSlideSummary:
    """Lightweight internal summary for one planned slide."""

    slide_title: str
    kind: str
    pattern_id: str
    layout_name: str
    continuation: bool
    text_slot_names: tuple[str, ...]
    image_slot_names: tuple[str, ...]
    visible_text: tuple[str, ...]


@dataclass(slots=True)
class GenerationSummary:
    """Internal deck summary that preview surfaces can consume."""

    slides: tuple[GenerationSlideSummary, ...]


def generate_report(request: ReportRequest) -> Path:
    """Generate a deck artifact from a structured request."""

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
    template_name: str = PUBLIC_BUILT_IN_TEMPLATE_NAME,
    image_refs: dict[str, Path] | None = None,
) -> Path:
    """Generate a deck artifact from an already-parsed mapping."""

    writer = PowerPointWriter()
    presentation = _prepare_presentation(
        writer,
        template_name=template_name,
        template_path=template_path,
    )
    artifacts = prepare_generation_artifacts_from_mapping(
        raw_data,
        presentation=presentation,
        template_path=template_path,
        template_name=template_name,
        image_refs=image_refs,
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
    template_name: str = PUBLIC_BUILT_IN_TEMPLATE_NAME,
    image_refs: dict[str, Path] | None = None,
) -> GenerationArtifacts:
    """Build the profiled template, validated payload, and fill plan."""

    template_profile, template_contract = _resolve_template_artifacts(
        presentation,
        template_path=template_path,
        template_name=template_name,
    )
    payload = validate_payload(
        raw_data,
        template_contract,
        available_image_refs=(image_refs or {}).keys(),
    )
    fill_plan, diagnostic_report = build_report_fill_plan(
        payload,
        template_profile,
        image_refs=image_refs,
    )
    return GenerationArtifacts(
        template_profile=template_profile,
        template_contract=template_contract,
        report_payload=payload,
        fill_plan=fill_plan,
        diagnostic_report=diagnostic_report,
        generation_summary=_build_generation_summary(fill_plan),
    )


def _resolve_template_artifacts(
    presentation,
    *,
    template_path: Path | None,
    template_name: str,
) -> tuple[TemplateProfile, TemplateContract]:
    if template_path is None:
        return get_built_in_profile(), get_built_in_contract()

    template_profile = profile_template(
        presentation,
        template_path=template_path,
        template_name=template_name,
    )
    return template_profile, export_template_contract(template_profile)


def _prepare_presentation(
    writer: PowerPointWriter,
    *,
    template_name: str,
    template_path: Path | None,
):
    if template_path is not None:
        return writer._load_presentation(template_path)
    return writer._load_presentation(None)


def _build_generation_summary(fill_plan: FillPlan) -> GenerationSummary:
    return GenerationSummary(
        slides=tuple(
            GenerationSlideSummary(
                slide_title=slide.slide_title,
                kind=slide.kind,
                pattern_id=slide.pattern_id,
                layout_name=slide.layout_name,
                continuation=slide.continuation,
                text_slot_names=tuple(
                    fill.slot.slot_name for fill in slide.text_fills
                ),
                image_slot_names=tuple(
                    fill.slot.slot_name for fill in slide.image_fills
                ),
                visible_text=_collect_visible_text(slide.text_fills),
            )
            for slide in fill_plan.slides
        )
    )


def _collect_visible_text(
    text_fills: list[PlannedTextFill],
) -> tuple[str, ...]:
    visible_text: list[str] = []
    for fill in text_fills:
        resolved = _resolve_visible_text(fill)
        if resolved:
            visible_text.append(resolved)
    return tuple(visible_text)


def _resolve_visible_text(fill: PlannedTextFill) -> str:
    if fill.text is not None:
        return fill.text
    return "\n".join(fill.items)
