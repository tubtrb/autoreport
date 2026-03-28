"""Template-aware autofill planning primitives and text-fitting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path


EMU_PER_POINT = 12700
DEFAULT_LINE_HEIGHT_FACTOR = 1.35
DEFAULT_CHAR_WIDTH_FACTOR = 0.52
DEFAULT_VERTICAL_PADDING_PT = 10
DEFAULT_HORIZONTAL_PADDING_PT = 12


class SlotContentKind(str, Enum):
    """Kinds of content blocks/slotted content supported by the autofill engine."""

    TITLE = "title"
    PARAGRAPH_OR_BULLETS = "paragraph_or_bullets"
    METRIC_LIST = "metric_list"
    SHORT_FACT_OR_STATUS = "short_fact_or_status"


class FitStatus(str, Enum):
    """High-level outcomes after attempting to fit content into a slot."""

    FIT = "fit"
    SHRINK = "shrink"
    SPILL = "spill"
    OVERFLOW = "overflow"


class DiagnosticSeverity(str, Enum):
    """Supported diagnostic levels for autofill and template checks."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True)
class SlotDescriptor:
    """Describes one fillable region inside a template layout."""

    slot_name: str
    layout_index: int
    placeholder_index: int | None
    x: int
    y: int
    width: int
    height: int
    preferred_font_size: int
    min_font_size: int
    allowed_kinds: tuple[SlotContentKind, ...]
    explicit_font_name: str | None = None
    priority: int = 0

    def supports(self, kind: SlotContentKind) -> bool:
        """Return whether this slot accepts the given content kind."""

        return kind in self.allowed_kinds

    def estimated_char_budget(self, font_size: int) -> int:
        """Estimate how many characters fit in this slot for a font size."""

        _, _, budget = calc_text_box(font_size, self)
        return budget


@dataclass(slots=True)
class TemplateProfile:
    """Summary of the layouts and slots used by a known template family."""

    template_name: str
    template_path: Path | None
    title_layout_index: int
    title_layout_name: str
    body_layout_index: int
    body_layout_name: str
    title_slot: SlotDescriptor
    subtitle_slot: SlotDescriptor
    body_title_slot: SlotDescriptor
    body_content_slot: SlotDescriptor
    title_secondary_slots: tuple[SlotDescriptor, ...] = ()
    body_content_slots: tuple[SlotDescriptor, ...] = ()


@dataclass(slots=True)
class ContentBlock:
    """One semantic unit of input content to map into a slide slot."""

    block_id: str
    kind: SlotContentKind
    heading: str
    items: list[str] = field(default_factory=list)
    secondary_text: str | None = None


@dataclass(slots=True)
class FitResult:
    """Result of fitting a content block into a slot."""

    status: FitStatus
    font_size: int
    consumed_items: int
    remaining_items: int
    out_of_bounds_risk: bool = False


@dataclass(slots=True)
class SlideDecoration:
    """A neutral non-text shape drawn as part of a planned slide."""

    shape_type: str
    x: int
    y: int
    width: int
    height: int
    fill_rgb: tuple[int, int, int]
    line_rgb: tuple[int, int, int] | None = None


@dataclass(slots=True)
class PlannedTextFill:
    """One text assignment targeting a specific slot on a slide."""

    slot: SlotDescriptor
    items: list[str] = field(default_factory=list)
    text: str | None = None
    font_size: int | None = None
    fit_result: FitResult | None = None


@dataclass(slots=True)
class PlannedSlide:
    """A slide ready to be written into a PowerPoint presentation."""

    layout_name: str
    layout_index: int
    title_slot: SlotDescriptor
    title_text: str
    content_kind: SlotContentKind
    source_block_id: str
    body_slot: SlotDescriptor | None = None
    subtitle_text: str | None = None
    body_items: list[str] = field(default_factory=list)
    title_font_size: int | None = None
    body_font_size: int | None = None
    fit_result: FitResult | None = None
    continuation: bool = False
    decorations: list[SlideDecoration] = field(default_factory=list)
    body_fills: list[PlannedTextFill] = field(default_factory=list)


@dataclass(slots=True)
class FillPlan:
    """Ordered slide-writing plan for one generated deck."""

    slides: list[PlannedSlide] = field(default_factory=list)


@dataclass(slots=True)
class DiagnosticEntry:
    """One diagnostic message emitted during template-aware planning."""

    severity: DiagnosticSeverity
    code: str
    message: str
    slide_title: str | None = None


@dataclass(slots=True)
class DiagnosticReport:
    """Aggregated warnings and errors from profiling and autofill passes."""

    entries: list[DiagnosticEntry] = field(default_factory=list)

    def add_warning(
        self,
        code: str,
        message: str,
        *,
        slide_title: str | None = None,
    ) -> None:
        """Record a warning entry."""

        self.entries.append(
            DiagnosticEntry(
                severity=DiagnosticSeverity.WARNING,
                code=code,
                message=message,
                slide_title=slide_title,
            )
        )

    def add_error(
        self,
        code: str,
        message: str,
        *,
        slide_title: str | None = None,
    ) -> None:
        """Record an error entry."""

        self.entries.append(
            DiagnosticEntry(
                severity=DiagnosticSeverity.ERROR,
                code=code,
                message=message,
                slide_title=slide_title,
            )
        )

    @property
    def warnings(self) -> list[DiagnosticEntry]:
        """Return only warning entries."""

        return [
            entry
            for entry in self.entries
            if entry.severity == DiagnosticSeverity.WARNING
        ]

    @property
    def errors(self) -> list[DiagnosticEntry]:
        """Return only error entries."""

        return [
            entry
            for entry in self.entries
            if entry.severity == DiagnosticSeverity.ERROR
        ]


def calc_text_box(
    font_size_pt: int,
    slot: SlotDescriptor,
) -> tuple[int, int, int]:
    """Estimate text-box geometry and capacity from slot size and font size."""

    width_pt = max(1.0, slot.width / EMU_PER_POINT)
    height_pt = max(1.0, slot.height / EMU_PER_POINT)
    usable_width_pt = max(1.0, width_pt - (DEFAULT_HORIZONTAL_PADDING_PT * 2))
    usable_height_pt = max(1.0, height_pt - (DEFAULT_VERTICAL_PADDING_PT * 2))

    chars_per_line = max(
        8,
        int(usable_width_pt / max(font_size_pt * DEFAULT_CHAR_WIDTH_FACTOR, 1.0)),
    )
    line_height_pt = font_size_pt * DEFAULT_LINE_HEIGHT_FACTOR
    line_count = max(1, int(usable_height_pt / max(line_height_pt, 1.0)))
    return chars_per_line, line_count, chars_per_line * line_count


def calc_text_box_height_simple(
    font_size_pt: int,
    num_lines: int,
    leading: float = DEFAULT_LINE_HEIGHT_FACTOR,
    padding: int = DEFAULT_VERTICAL_PADDING_PT,
) -> float:
    """Quick text height estimate inspired by the slide-helper workflow."""

    return (font_size_pt * leading * max(num_lines, 1)) + (padding * 2)


def estimate_text_load(items: list[str]) -> int:
    """Approximate the text load of bullet items for fitting decisions."""

    total = 0
    for item in items:
        line_count = max(1, item.count("\n") + 1)
        total += len(item) + (line_count * 4)
    return total


def estimate_wrapped_line_count(text: str, chars_per_line: int) -> int:
    """Estimate wrapped line usage for one logical text item."""

    safe_chars_per_line = max(chars_per_line, 1)
    raw_lines = text.splitlines() or [text]
    wrapped_lines = 0
    for raw_line in raw_lines:
        wrapped_lines += max(1, math.ceil(len(raw_line) / safe_chars_per_line))
    return wrapped_lines


def estimate_item_line_usage(
    items: list[str],
    chars_per_line: int,
) -> int:
    """Estimate total wrapped lines used by a list of items."""

    return sum(
        estimate_wrapped_line_count(item, chars_per_line)
        for item in items
    )


def iter_font_sizes(preferred_font_size: int, min_font_size: int) -> list[int]:
    """Return the font sizes to try, from preferred size down to the minimum."""

    if preferred_font_size <= min_font_size:
        return [min_font_size]

    sizes = list(range(preferred_font_size, min_font_size - 1, -2))
    if sizes[-1] != min_font_size:
        sizes.append(min_font_size)
    return sizes


def fit_text_items_to_slot(
    items: list[str],
    slot: SlotDescriptor,
) -> FitResult:
    """Choose a font size or split point for a list of text items."""

    for font_size in iter_font_sizes(
        slot.preferred_font_size,
        slot.min_font_size,
    ):
        chars_per_line, line_count, _ = calc_text_box(font_size, slot)
        used_lines = estimate_item_line_usage(items, chars_per_line)
        if used_lines <= line_count:
            status = (
                FitStatus.FIT
                if font_size == slot.preferred_font_size
                else FitStatus.SHRINK
            )
            return FitResult(
                status=status,
                font_size=font_size,
                consumed_items=len(items),
                remaining_items=0,
            )

    chars_per_line, line_count, _ = calc_text_box(slot.min_font_size, slot)
    consumed_items: list[str] = []
    consumed_lines = 0
    out_of_bounds_risk = False

    for item in items:
        item_lines = estimate_wrapped_line_count(item, chars_per_line)
        if not consumed_items and item_lines > line_count:
            consumed_items.append(item)
            out_of_bounds_risk = True
            break

        if consumed_items and consumed_lines + item_lines > line_count:
            break

        consumed_items.append(item)
        consumed_lines += item_lines

    if not consumed_items:
        consumed_items.append(items[0])
        out_of_bounds_risk = True

    consumed_count = len(consumed_items)
    remaining_items = max(len(items) - consumed_count, 0)
    status = (
        FitStatus.OVERFLOW
        if out_of_bounds_risk
        else FitStatus.SPILL
    )
    return FitResult(
        status=status,
        font_size=slot.min_font_size,
        consumed_items=consumed_count,
        remaining_items=remaining_items,
        out_of_bounds_risk=out_of_bounds_risk,
    )


def fit_text_to_slot(text: str, slot: SlotDescriptor) -> FitResult:
    """Fit one logical text block into a slot."""

    return fit_text_items_to_slot([text], slot)


def sort_slots_in_reading_order(
    slots: list[SlotDescriptor] | tuple[SlotDescriptor, ...],
) -> list[SlotDescriptor]:
    """Return slots sorted in a top-to-bottom, left-to-right reading order."""

    ordered = sorted(slots, key=lambda slot: (slot.y, slot.x))
    if len(ordered) <= 1:
        return ordered

    row_threshold = max(slot.height for slot in ordered) // 3
    rows: list[list[SlotDescriptor]] = []
    for slot in ordered:
        if rows and abs(rows[-1][0].y - slot.y) <= row_threshold:
            rows[-1].append(slot)
            continue
        rows.append([slot])

    flattened: list[SlotDescriptor] = []
    for row in rows:
        flattened.extend(sorted(row, key=lambda slot: slot.x))
    return flattened
