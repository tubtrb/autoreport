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
    PlannedTextFill,
    PlannedSlide,
    SlotContentKind,
    SlotDescriptor,
    TemplateProfile,
    fit_text_items_to_slot,
    fit_text_to_slot,
    sort_slots_in_reading_order,
)


TEMPLATE_NAME = "weekly_report"
BASIC_TEMPLATE_NAME = "basic_template"
SUPPORTED_TEMPLATE_NAMES = (
    TEMPLATE_NAME,
    BASIC_TEMPLATE_NAME,
)
TITLE_LAYOUT_INDEX = 0
BODY_LAYOUT_INDEX = 1
BLANK_LAYOUT_INDEX = 6
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
BASIC_TITLE_FONT_SIZE = 28
BASIC_TITLE_MIN_FONT_SIZE = 20
BASIC_SUBTITLE_FONT_SIZE = 18
BASIC_SUBTITLE_MIN_FONT_SIZE = 14
BASIC_SECTION_TITLE_FONT_SIZE = 24
BASIC_SECTION_TITLE_MIN_FONT_SIZE = 20
BASIC_SECTION_BODY_FONT_SIZE = 20
BASIC_SECTION_BODY_MIN_FONT_SIZE = 14

IGNORED_TEXT_PLACEHOLDER_TYPES = frozenset(
    getattr(PP_PLACEHOLDER, name)
    for name in ("DATE", "FOOTER", "SLIDE_NUMBER")
    if hasattr(PP_PLACEHOLDER, name)
)


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
    body_blocks = [
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
    return [
        ContentBlock(
            block_id="title",
            kind=SlotContentKind.TITLE,
            heading=report.title,
            secondary_text=f"{report.team}\n{report.week}",
        ),
        ContentBlock(
            block_id="contents",
            kind=SlotContentKind.SHORT_FACT_OR_STATUS,
            heading="Contents",
            items=[block.heading for block in body_blocks],
        ),
        *body_blocks,
    ]


def profile_weekly_template(
    presentation: Presentation,
    *,
    template_path: Path | None,
) -> TemplateProfile:
    """Profile the current title/content layouts into autofill slots."""

    (
        title_layout_index,
        title_layout,
        title_placeholder,
        title_secondary_placeholders,
    ) = _select_title_layout(
        presentation,
        template_path=template_path,
    )
    (
        body_layout_index,
        body_layout,
        body_title_placeholder,
        body_content_placeholders,
    ) = _select_body_layout(
        presentation,
        template_path=template_path,
        preferred_skip_layout_index=title_layout_index,
    )

    title_secondary_slots = tuple(
        _build_slot_descriptor(
            placeholder,
            layout_index=title_layout_index,
            slot_name=f"title_secondary_{index + 1}",
            preferred_font_size=SUBTITLE_FONT_SIZE,
            min_font_size=SUBTITLE_MIN_FONT_SIZE,
            allowed_kinds=(SlotContentKind.SHORT_FACT_OR_STATUS,),
        )
        for index, placeholder in enumerate(title_secondary_placeholders)
    )
    body_content_slots = tuple(
        _build_slot_descriptor(
            placeholder,
            layout_index=body_layout_index,
            slot_name=f"body_content_{index + 1}",
            preferred_font_size=SECTION_BODY_FONT_SIZE,
            min_font_size=SECTION_BODY_MIN_FONT_SIZE,
            allowed_kinds=(
                SlotContentKind.PARAGRAPH_OR_BULLETS,
                SlotContentKind.METRIC_LIST,
                SlotContentKind.SHORT_FACT_OR_STATUS,
            ),
        )
        for index, placeholder in enumerate(body_content_placeholders)
    )

    return TemplateProfile(
        template_name=TEMPLATE_NAME,
        template_path=template_path,
        title_layout_index=title_layout_index,
        title_layout_name=title_layout.name,
        body_layout_index=body_layout_index,
        body_layout_name=body_layout.name,
        title_slot=_build_slot_descriptor(
            title_placeholder,
            layout_index=title_layout_index,
            slot_name="title_title",
            preferred_font_size=TITLE_FONT_SIZE,
            min_font_size=TITLE_MIN_FONT_SIZE,
            allowed_kinds=(SlotContentKind.TITLE,),
        ),
        subtitle_slot=title_secondary_slots[0],
        body_title_slot=_build_slot_descriptor(
            body_title_placeholder,
            layout_index=body_layout_index,
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
        body_content_slot=body_content_slots[0],
        title_secondary_slots=title_secondary_slots,
        body_content_slots=body_content_slots,
    )


def profile_basic_template(
    presentation: Presentation,
    *,
    template_path: Path | None,
) -> TemplateProfile:
    """Build a neutral text-first profile derived from the sanitized sample deck."""

    blank_layout = _get_layout(
        presentation,
        layout_index=BLANK_LAYOUT_INDEX,
        layout_name="blank",
        template_path=template_path,
    )

    title_slot = _build_text_box_slot(
        presentation,
        layout_index=BLANK_LAYOUT_INDEX,
        slot_name="title_title",
        x_ratio=0.054,
        y_ratio=0.160,
        width_ratio=0.824,
        height_ratio=0.104,
        preferred_font_size=BASIC_TITLE_FONT_SIZE,
        min_font_size=BASIC_TITLE_MIN_FONT_SIZE,
        allowed_kinds=(SlotContentKind.TITLE,),
    )
    subtitle_slot = _build_text_box_slot(
        presentation,
        layout_index=BLANK_LAYOUT_INDEX,
        slot_name="title_subtitle",
        x_ratio=0.053,
        y_ratio=0.561,
        width_ratio=0.235,
        height_ratio=0.247,
        preferred_font_size=BASIC_SUBTITLE_FONT_SIZE,
        min_font_size=BASIC_SUBTITLE_MIN_FONT_SIZE,
        allowed_kinds=(SlotContentKind.SHORT_FACT_OR_STATUS,),
    )
    body_title_slot = _build_text_box_slot(
        presentation,
        layout_index=BLANK_LAYOUT_INDEX,
        slot_name="body_title",
        x_ratio=0.029,
        y_ratio=0.013,
        width_ratio=0.863,
        height_ratio=0.071,
        preferred_font_size=BASIC_SECTION_TITLE_FONT_SIZE,
        min_font_size=BASIC_SECTION_TITLE_MIN_FONT_SIZE,
        allowed_kinds=(
            SlotContentKind.TITLE,
            SlotContentKind.PARAGRAPH_OR_BULLETS,
            SlotContentKind.METRIC_LIST,
            SlotContentKind.SHORT_FACT_OR_STATUS,
        ),
    )
    body_content_slot = _build_text_box_slot(
        presentation,
        layout_index=BLANK_LAYOUT_INDEX,
        slot_name="body_content",
        x_ratio=0.048,
        y_ratio=0.220,
        width_ratio=0.904,
        height_ratio=0.640,
        preferred_font_size=BASIC_SECTION_BODY_FONT_SIZE,
        min_font_size=BASIC_SECTION_BODY_MIN_FONT_SIZE,
        allowed_kinds=(
            SlotContentKind.PARAGRAPH_OR_BULLETS,
            SlotContentKind.METRIC_LIST,
            SlotContentKind.SHORT_FACT_OR_STATUS,
        ),
    )

    return TemplateProfile(
        template_name=BASIC_TEMPLATE_NAME,
        template_path=None,
        title_layout_index=BLANK_LAYOUT_INDEX,
        title_layout_name=blank_layout.name,
        body_layout_index=BLANK_LAYOUT_INDEX,
        body_layout_name=blank_layout.name,
        title_slot=title_slot,
        subtitle_slot=subtitle_slot,
        body_title_slot=body_title_slot,
        body_content_slot=body_content_slot,
        title_secondary_slots=(subtitle_slot,),
        body_content_slots=(body_content_slot,),
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
            subtitle_items = [
                item.strip()
                for item in (block.secondary_text or "").splitlines()
                if item.strip()
            ]
            subtitle_fills, _ = _plan_items_across_slots(
                subtitle_items,
                template_profile.title_secondary_slots
                or (template_profile.subtitle_slot,),
                reserve_one_item_per_remaining_slot=True,
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
                    subtitle_text="\n".join(subtitle_items),
                    title_font_size=title_fit.font_size,
                    body_font_size=(
                        subtitle_fills[0].font_size
                        if subtitle_fills
                        else None
                    ),
                    fit_result=(
                        subtitle_fills[-1].fit_result
                        if subtitle_fills
                        else None
                    ),
                    body_fills=subtitle_fills,
                )
            )
            _record_fit_diagnostics(
                diagnostics,
                slide_title=block.heading,
                fit_result=title_fit,
                label="title",
            )
            for index, fill in enumerate(subtitle_fills, start=1):
                if fill.fit_result is None:
                    continue
                _record_fit_diagnostics(
                    diagnostics,
                    slide_title=block.heading,
                    fit_result=fill.fit_result,
                    label=f"subtitle slot {index}",
                )
            continue

        remaining_items = list(block.items)
        continuation_index = 0
        while remaining_items:
            continuation = continuation_index > 0
            slide_title = (
                f"{block.heading} (cont.)"
                if continuation
                else block.heading
            )
            body_title_fit = fit_text_to_slot(
                slide_title,
                template_profile.body_title_slot,
            )
            body_fills, remaining_items = _plan_items_across_slots(
                remaining_items,
                template_profile.body_content_slots
                or (template_profile.body_content_slot,),
                reserve_one_item_per_remaining_slot=True,
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
                    body_items=[
                        item
                        for fill in body_fills
                        for item in fill.items
                    ],
                    title_font_size=body_title_fit.font_size,
                    body_font_size=(
                        body_fills[0].font_size
                        if body_fills
                        else None
                    ),
                    fit_result=(
                        body_fills[-1].fit_result
                        if body_fills
                        else None
                    ),
                    continuation=continuation,
                    body_fills=body_fills,
                )
            )
            _record_fit_diagnostics(
                diagnostics,
                slide_title=slide_title,
                fit_result=body_title_fit,
                label=f"{block.heading} title",
            )
            for index, fill in enumerate(body_fills, start=1):
                if fill.fit_result is None:
                    continue
                _record_fit_diagnostics(
                    diagnostics,
                    slide_title=slide_title,
                    fit_result=fill.fit_result,
                    label=f"{block.heading} slot {index}",
                )
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


def _select_title_layout(
    presentation: Presentation,
    *,
    template_path: Path | None,
):
    for layout_index, layout in enumerate(presentation.slide_layouts):
        try:
            title_placeholder = _pick_title_text_placeholder(
                layout,
                layout_name="title",
                template_path=template_path,
            )
            subtitle_placeholders = _pick_title_secondary_text_placeholders(
                layout,
                excluded_idx=title_placeholder.placeholder_format.idx,
                anchor_top=title_placeholder.top,
                layout_name="title",
                template_path=template_path,
            )
            return (
                layout_index,
                layout,
                title_placeholder,
                subtitle_placeholders,
            )
        except TemplateCompatibilityError:
            continue

    raise TemplateCompatibilityError(
        template_path,
        "no compatible title layout exposing both title and subtitle placeholders",
    )


def _select_body_layout(
    presentation: Presentation,
    *,
    template_path: Path | None,
    preferred_skip_layout_index: int | None = None,
):
    candidate_indices = [
        index
        for index, _ in enumerate(presentation.slide_layouts)
        if index != preferred_skip_layout_index
    ]
    best_candidate = None

    for layout_index in candidate_indices:
        layout = presentation.slide_layouts[layout_index]
        try:
            body_title_placeholder = _pick_body_title_placeholder(
                layout,
                layout_name="body",
                template_path=template_path,
            )
            body_content_placeholders = _pick_body_content_placeholders(
                layout,
                excluded_idx=body_title_placeholder.placeholder_format.idx,
                layout_name="body",
                template_path=template_path,
            )
            candidate = (
                len(body_content_placeholders),
                sum(
                    placeholder.width * placeholder.height
                    for placeholder in body_content_placeholders
                ),
                -layout_index,
                layout_index,
                layout,
                body_title_placeholder,
                body_content_placeholders,
            )
            if best_candidate is None or candidate > best_candidate:
                best_candidate = candidate
        except TemplateCompatibilityError:
            continue

    if best_candidate is None:
        raise TemplateCompatibilityError(
            template_path,
            "no compatible body layout exposing both title and content placeholders",
        )

    _, _, _, layout_index, layout, body_title_placeholder, body_content_placeholders = best_candidate
    return (
        layout_index,
        layout,
        body_title_placeholder,
        body_content_placeholders,
    )


def _require_title_placeholder(
    layout,
    *,
    layout_name: str,
    template_path: Path | None,
):
    placeholder = _find_title_placeholder(layout)
    if placeholder is not None:
        return placeholder

    raise TemplateCompatibilityError(
        template_path,
        f"'{layout_name}' layout has no title placeholder",
    )


def _find_title_placeholder(layout):
    for placeholder in getattr(layout, "placeholders", []):
        placeholder_type = placeholder.placeholder_format.type
        if placeholder_type in (
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
        ) and hasattr(placeholder, "text_frame"):
            return placeholder

    return None


def _pick_title_text_placeholder(
    layout,
    *,
    layout_name: str,
    template_path: Path | None,
):
    placeholder = _find_title_placeholder(layout)
    if placeholder is not None:
        return placeholder

    candidates = _list_text_placeholders(layout)
    if not candidates:
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no text placeholder",
        )

    return max(candidates, key=lambda shape: shape.width * shape.height)


def _pick_body_title_placeholder(
    layout,
    *,
    layout_name: str,
    template_path: Path | None,
):
    placeholder = _find_title_placeholder(layout)
    if placeholder is not None:
        return placeholder

    candidates = _list_text_placeholders(layout)
    if len(candidates) < 2:
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no title-like text placeholder",
        )

    return min(candidates, key=lambda shape: (shape.top, shape.left))


def _pick_primary_text_placeholder(
    layout,
    *,
    excluded_idx: int,
    layout_name: str,
    template_path: Path | None,
    required: bool = True,
):
    candidates = _list_text_placeholders(layout, excluded_idx=excluded_idx)
    if not candidates:
        if not required:
            return None
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no secondary text placeholder",
        )
    return max(candidates, key=lambda shape: shape.width * shape.height)


def _pick_title_secondary_text_placeholders(
    layout,
    *,
    excluded_idx: int,
    anchor_top: int,
    layout_name: str,
    template_path: Path | None,
):
    candidates = _list_text_placeholders(layout, excluded_idx=excluded_idx)
    if not candidates:
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no secondary text placeholder",
        )

    lower_candidates = [
        shape
        for shape in candidates
        if shape.top >= anchor_top
    ]
    scoped_candidates = lower_candidates or candidates
    max_area = max(shape.width * shape.height for shape in scoped_candidates)
    prominent_candidates = [
        shape
        for shape in scoped_candidates
        if (shape.width * shape.height) >= (max_area * 0.45)
    ]
    return tuple(
        sorted(prominent_candidates, key=lambda shape: (shape.top, shape.left))
    )


def _pick_body_content_placeholders(
    layout,
    *,
    excluded_idx: int,
    layout_name: str,
    template_path: Path | None,
):
    candidates = _list_text_placeholders(layout, excluded_idx=excluded_idx)
    if not candidates:
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no secondary text placeholder",
        )

    max_area = max(shape.width * shape.height for shape in candidates)
    prominent_candidates = [
        shape
        for shape in candidates
        if (shape.width * shape.height) >= (max_area * 0.6)
    ] or [max(candidates, key=lambda shape: shape.width * shape.height)]
    return tuple(
        sorted(prominent_candidates, key=lambda shape: (shape.top, shape.left))
    )


def _pick_secondary_text_placeholder(
    layout,
    *,
    excluded_idx: int,
    anchor_top: int,
    layout_name: str,
    template_path: Path | None,
):
    candidates = _pick_title_secondary_text_placeholders(
        layout,
        excluded_idx=excluded_idx,
        anchor_top=anchor_top,
        layout_name=layout_name,
        template_path=template_path,
    )
    if not candidates:
        raise TemplateCompatibilityError(
            template_path,
            f"'{layout_name}' layout has no secondary text placeholder",
        )
    return candidates[0]


def _plan_items_across_slots(
    items: list[str],
    slots: tuple[SlotDescriptor, ...] | list[SlotDescriptor],
    *,
    reserve_one_item_per_remaining_slot: bool,
) -> tuple[list[PlannedTextFill], list[str]]:
    fills: list[PlannedTextFill] = []
    remaining_items = list(items)
    ordered_slots = sort_slots_in_reading_order(list(slots))

    for index, slot in enumerate(ordered_slots):
        if not remaining_items:
            break

        remaining_slot_count = len(ordered_slots) - index - 1
        max_items_for_slot = len(remaining_items)
        if reserve_one_item_per_remaining_slot and remaining_slot_count > 0:
            max_items_for_slot = max(
                1,
                len(remaining_items) - remaining_slot_count,
            )
        candidate_items = remaining_items[:max_items_for_slot]
        fit_result = fit_text_items_to_slot(candidate_items, slot)
        consumed_items = candidate_items[: fit_result.consumed_items]
        fills.append(
            PlannedTextFill(
                slot=slot,
                items=consumed_items,
                font_size=fit_result.font_size,
                fit_result=fit_result,
            )
        )
        remaining_items = remaining_items[len(consumed_items) :]

    return fills, remaining_items


def _list_text_placeholders(layout, *, excluded_idx: int | None = None):
    return [
        shape
        for shape in layout.placeholders
        if hasattr(shape, "text_frame")
        and shape.placeholder_format.type not in IGNORED_TEXT_PLACEHOLDER_TYPES
        and (
            excluded_idx is None
            or shape.placeholder_format.idx != excluded_idx
        )
    ]


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


def _build_text_box_slot(
    presentation: Presentation,
    *,
    layout_index: int,
    slot_name: str,
    x_ratio: float,
    y_ratio: float,
    width_ratio: float,
    height_ratio: float,
    preferred_font_size: int,
    min_font_size: int,
    allowed_kinds: tuple[SlotContentKind, ...],
) -> SlotDescriptor:
    return SlotDescriptor(
        slot_name=slot_name,
        layout_index=layout_index,
        placeholder_index=None,
        x=int(presentation.slide_width * x_ratio),
        y=int(presentation.slide_height * y_ratio),
        width=int(presentation.slide_width * width_ratio),
        height=int(presentation.slide_height * height_ratio),
        preferred_font_size=preferred_font_size,
        min_font_size=min_font_size,
        allowed_kinds=allowed_kinds,
    )


def _add_font_risk_warnings(
    diagnostics: DiagnosticReport,
    template_profile: TemplateProfile,
) -> None:
    if template_profile.template_path is None:
        return

    slots = [
        template_profile.title_slot,
        template_profile.body_title_slot,
    ]
    slots.extend(template_profile.title_secondary_slots or (template_profile.subtitle_slot,))
    slots.extend(template_profile.body_content_slots or (template_profile.body_content_slot,))

    for slot in slots:
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
