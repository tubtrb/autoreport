"""Template helpers for weekly report slide generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from autoreport.models import WeeklyReport
from autoreport.outputs.errors import TemplateCompatibilityError
from autoreport.templates.autofill import (
    ContentBlock,
    DiagnosticReport,
    FillPlan,
    FitStatus,
    PlannedSlide,
    SlotContentKind,
    SlotDescriptor,
    TemplateProfile,
    fit_text_items_to_slot,
    fit_text_to_slot,
)


TEMPLATE_NAME = "weekly_report"
TITLE_LAYOUT_INDEX = 0
BODY_LAYOUT_INDEX = 1
METRIC_LABELS = (
    ("tasks_completed", "Tasks completed"),
    ("open_issues", "Open issues"),
)
TITLE_FONT_SIZE = 30
TITLE_MIN_FONT_SIZE = 22
SUBTITLE_FONT_SIZE = 18
SUBTITLE_MIN_FONT_SIZE = 14
SECTION_TITLE_FONT_SIZE = 24
SECTION_BODY_FONT_SIZE = 18
SECTION_BODY_MIN_FONT_SIZE = 14


def build_weekly_report_context(report: WeeklyReport) -> dict[str, Any]:
    """Prepare slide-friendly context for a weekly report presentation."""

    metric_items = [
        f"{label}: {report.metrics[key]}"
        for key, label in METRIC_LABELS
    ]

    return {
        "slides": [
            {
                "layout": "title",
                "title": report.title,
                "subtitle": f"{report.team}\n{report.week}",
            },
            {
                "layout": "bullets",
                "title": "Highlights",
                "items": list(report.highlights),
            },
            {
                "layout": "bullets",
                "title": "Metrics",
                "items": metric_items,
            },
            {
                "layout": "bullets",
                "title": "Risks",
                "items": list(report.risks),
            },
            {
                "layout": "bullets",
                "title": "Next Steps",
                "items": list(report.next_steps),
            },
        ]
    }


def build_weekly_report_content_blocks(report: WeeklyReport) -> list[ContentBlock]:
    """Convert validated report data into template-aware content blocks."""

    metric_items = [
        f"{label}: {report.metrics[key]}"
        for key, label in METRIC_LABELS
    ]
    return [
        ContentBlock(
            block_id="title",
            kind=SlotContentKind.TITLE,
            heading=report.title,
            secondary_text=f"{report.team}\n{report.week}",
        ),
        ContentBlock(
            block_id="highlights",
            kind=SlotContentKind.PARAGRAPH_OR_BULLETS,
            heading="Highlights",
            items=list(report.highlights),
        ),
        ContentBlock(
            block_id="metrics",
            kind=SlotContentKind.METRIC_LIST,
            heading="Metrics",
            items=metric_items,
        ),
        ContentBlock(
            block_id="risks",
            kind=SlotContentKind.SHORT_FACT_OR_STATUS,
            heading="Risks",
            items=list(report.risks),
        ),
        ContentBlock(
            block_id="next_steps",
            kind=SlotContentKind.SHORT_FACT_OR_STATUS,
            heading="Next Steps",
            items=list(report.next_steps),
        ),
    ]


def profile_weekly_template(
    presentation: Presentation,
    *,
    template_path: Path | None,
) -> TemplateProfile:
    """Profile the current title/content layouts into autofill slots."""

    title_layout = _get_layout(
        presentation,
        layout_index=TITLE_LAYOUT_INDEX,
        layout_name="title",
        template_path=template_path,
    )
    body_layout = _get_layout(
        presentation,
        layout_index=BODY_LAYOUT_INDEX,
        layout_name="body",
        template_path=template_path,
    )

    title_placeholder = _require_title_placeholder(
        title_layout,
        layout_name="title",
        template_path=template_path,
    )
    subtitle_placeholder = _pick_primary_text_placeholder(
        title_layout,
        excluded_idx=title_placeholder.placeholder_format.idx,
        layout_name="title",
        template_path=template_path,
    )
    body_title_placeholder = _require_title_placeholder(
        body_layout,
        layout_name="body",
        template_path=template_path,
    )
    body_content_placeholder = _pick_primary_text_placeholder(
        body_layout,
        excluded_idx=body_title_placeholder.placeholder_format.idx,
        layout_name="body",
        template_path=template_path,
    )

    return TemplateProfile(
        template_name=TEMPLATE_NAME,
        template_path=template_path,
        title_layout_index=TITLE_LAYOUT_INDEX,
        title_layout_name=title_layout.name,
        body_layout_index=BODY_LAYOUT_INDEX,
        body_layout_name=body_layout.name,
        title_slot=_build_slot_descriptor(
            title_placeholder,
            layout_index=TITLE_LAYOUT_INDEX,
            slot_name="title_title",
            preferred_font_size=TITLE_FONT_SIZE,
            min_font_size=TITLE_MIN_FONT_SIZE,
            allowed_kinds=(SlotContentKind.TITLE,),
        ),
        subtitle_slot=_build_slot_descriptor(
            subtitle_placeholder,
            layout_index=TITLE_LAYOUT_INDEX,
            slot_name="title_subtitle",
            preferred_font_size=SUBTITLE_FONT_SIZE,
            min_font_size=SUBTITLE_MIN_FONT_SIZE,
            allowed_kinds=(SlotContentKind.SHORT_FACT_OR_STATUS,),
        ),
        body_title_slot=_build_slot_descriptor(
            body_title_placeholder,
            layout_index=BODY_LAYOUT_INDEX,
            slot_name="body_title",
            preferred_font_size=SECTION_TITLE_FONT_SIZE,
            min_font_size=SECTION_TITLE_FONT_SIZE,
            allowed_kinds=(
                SlotContentKind.TITLE,
                SlotContentKind.PARAGRAPH_OR_BULLETS,
                SlotContentKind.METRIC_LIST,
                SlotContentKind.SHORT_FACT_OR_STATUS,
            ),
        ),
        body_content_slot=_build_slot_descriptor(
            body_content_placeholder,
            layout_index=BODY_LAYOUT_INDEX,
            slot_name="body_content",
            preferred_font_size=SECTION_BODY_FONT_SIZE,
            min_font_size=SECTION_BODY_MIN_FONT_SIZE,
            allowed_kinds=(
                SlotContentKind.PARAGRAPH_OR_BULLETS,
                SlotContentKind.METRIC_LIST,
                SlotContentKind.SHORT_FACT_OR_STATUS,
            ),
        ),
    )


def build_weekly_report_fill_plan(
    content_blocks: list[ContentBlock],
    template_profile: TemplateProfile,
) -> tuple[FillPlan, DiagnosticReport]:
    """Map content blocks into concrete slides for the current template."""

    fill_plan = FillPlan()
    diagnostics = DiagnosticReport()
    _add_font_risk_warnings(diagnostics, template_profile)

    for block in content_blocks:
        if block.kind == SlotContentKind.TITLE:
            title_fit = fit_text_to_slot(
                block.heading,
                template_profile.title_slot,
            )
            subtitle_text = block.secondary_text or ""
            subtitle_fit = fit_text_to_slot(
                subtitle_text,
                template_profile.subtitle_slot,
            )
            fill_plan.slides.append(
                PlannedSlide(
                    layout_name=template_profile.title_layout_name,
                    layout_index=template_profile.title_layout_index,
                    title_slot=template_profile.title_slot,
                    title_text=block.heading,
                    content_kind=block.kind,
                    source_block_id=block.block_id,
                    body_slot=template_profile.subtitle_slot,
                    subtitle_text=subtitle_text,
                    title_font_size=title_fit.font_size,
                    body_font_size=subtitle_fit.font_size,
                    fit_result=subtitle_fit,
                )
            )
            _record_fit_diagnostics(
                diagnostics,
                slide_title=block.heading,
                fit_result=title_fit,
                label="title",
            )
            _record_fit_diagnostics(
                diagnostics,
                slide_title=block.heading,
                fit_result=subtitle_fit,
                label="subtitle",
            )
            continue

        remaining_items = list(block.items)
        continuation_index = 0
        while remaining_items:
            fit_result = fit_text_items_to_slot(
                remaining_items,
                template_profile.body_content_slot,
            )
            consumed_items = remaining_items[: fit_result.consumed_items]
            continuation = continuation_index > 0
            slide_title = (
                f"{block.heading} (cont.)"
                if continuation
                else block.heading
            )
            fill_plan.slides.append(
                PlannedSlide(
                    layout_name=template_profile.body_layout_name,
                    layout_index=template_profile.body_layout_index,
                    title_slot=template_profile.body_title_slot,
                    title_text=slide_title,
                    content_kind=block.kind,
                    source_block_id=block.block_id,
                    body_slot=template_profile.body_content_slot,
                    body_items=consumed_items,
                    title_font_size=SECTION_TITLE_FONT_SIZE,
                    body_font_size=fit_result.font_size,
                    fit_result=fit_result,
                    continuation=continuation,
                )
            )
            _record_fit_diagnostics(
                diagnostics,
                slide_title=slide_title,
                fit_result=fit_result,
                label=block.heading,
            )
            remaining_items = remaining_items[fit_result.consumed_items :]
            continuation_index += 1

    return fill_plan, diagnostics


def _get_layout(
    presentation: Presentation,
    *,
    layout_index: int,
    layout_name: str,
    template_path: Path | None,
):
    try:
        return presentation.slide_layouts[layout_index]
    except IndexError as exc:
        raise TemplateCompatibilityError(
            template_path,
            f"missing '{layout_name}' slide layout at index {layout_index}",
        ) from exc


def _require_title_placeholder(
    layout,
    *,
    layout_name: str,
    template_path: Path | None,
):
    for placeholder in getattr(layout, "placeholders", []):
        placeholder_type = placeholder.placeholder_format.type
        if placeholder_type in (
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
        ) and hasattr(placeholder, "text_frame"):
            return placeholder

    raise TemplateCompatibilityError(
        template_path,
        f"'{layout_name}' layout has no title placeholder",
    )


def _pick_primary_text_placeholder(
    layout,
    *,
    excluded_idx: int,
    layout_name: str,
    template_path: Path | None,
):
    candidates = [
        shape
        for shape in layout.placeholders
        if shape.placeholder_format.idx != excluded_idx
        and hasattr(shape, "text_frame")
    ]
    if not candidates:
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no secondary text placeholder",
        )
    return max(candidates, key=lambda shape: shape.width * shape.height)


def _build_slot_descriptor(
    placeholder,
    *,
    layout_index: int,
    slot_name: str,
    preferred_font_size: int,
    min_font_size: int,
    allowed_kinds: tuple[SlotContentKind, ...],
) -> SlotDescriptor:
    paragraph = placeholder.text_frame.paragraphs[0]
    return SlotDescriptor(
        slot_name=slot_name,
        layout_index=layout_index,
        placeholder_index=placeholder.placeholder_format.idx,
        x=placeholder.left,
        y=placeholder.top,
        width=placeholder.width,
        height=placeholder.height,
        preferred_font_size=preferred_font_size,
        min_font_size=min_font_size,
        allowed_kinds=allowed_kinds,
        explicit_font_name=paragraph.font.name,
    )


def _add_font_risk_warnings(
    diagnostics: DiagnosticReport,
    template_profile: TemplateProfile,
) -> None:
    if template_profile.template_path is None:
        return

    for slot in (
        template_profile.title_slot,
        template_profile.subtitle_slot,
        template_profile.body_title_slot,
        template_profile.body_content_slot,
    ):
        if slot.explicit_font_name is None:
            diagnostics.add_warning(
                "font-substitution-risk",
                "Template slot "
                f"'{slot.slot_name}' does not pin a font face; output may vary "
                "across machines.",
            )


def _record_fit_diagnostics(
    diagnostics: DiagnosticReport,
    *,
    slide_title: str,
    fit_result,
    label: str,
) -> None:
    if fit_result.status == FitStatus.SHRINK:
        diagnostics.add_warning(
            "font-shrink",
            f"{label} was shrunk to {fit_result.font_size}pt to fit the template.",
            slide_title=slide_title,
        )
    if fit_result.status in (FitStatus.SPILL, FitStatus.OVERFLOW):
        diagnostics.add_warning(
            "overflow-spill",
            f"{label} exceeded the slot budget and continued onto another slide.",
            slide_title=slide_title,
        )
    if fit_result.out_of_bounds_risk:
        diagnostics.add_warning(
            "out-of-bounds-risk",
            f"{label} may still exceed the safe text box bounds at "
            f"{fit_result.font_size}pt.",
            slide_title=slide_title,
        )
