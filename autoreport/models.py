"""Shared data models used across loading, validation, and generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TEMPLATE_CONTRACT_VERSION = "autoreport.template.v1"
REPORT_PAYLOAD_VERSION = "autoreport.payload.v1"


@dataclass(slots=True)
class ReportRequest:
    """Represents a generation request received from a public entrypoint."""

    source_path: Path
    output_path: Path | None = None
    template_path: Path | None = None
    template_name: str = "autoreport_editorial"


@dataclass(slots=True)
class WeeklyReport:
    """Legacy weekly report model kept for internal migration helpers."""

    title: str
    team: str
    week: str
    highlights: list[str]
    metrics: dict[str, int]
    risks: list[str]
    next_steps: list[str]


@dataclass(slots=True)
class TemplateSlotContract:
    """Public contract description for a single fillable template slot."""

    slot_id: str
    alias: str
    slot_type: str
    required: bool
    orientation: str | None = None
    order: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "slot_id": self.slot_id,
            "alias": self.alias,
            "slot_type": self.slot_type,
            "required": self.required,
        }
        if self.orientation is not None:
            payload["orientation"] = self.orientation
        if self.order is not None:
            payload["order"] = self.order
        return payload


@dataclass(slots=True)
class TemplatePatternContract:
    """Public contract for one reusable slide-generation pattern."""

    pattern_id: str
    kind: str
    layout_name: str
    slots: tuple[TemplateSlotContract, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "kind": self.kind,
            "layout_name": self.layout_name,
            "slots": [slot.to_dict() for slot in self.slots],
        }


@dataclass(slots=True)
class TemplateSectionContract:
    """Public contract for title/contents system slide sections."""

    pattern_id: str
    layout_name: str
    slots: tuple[TemplateSlotContract, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "layout_name": self.layout_name,
            "slots": [slot.to_dict() for slot in self.slots],
        }


@dataclass(slots=True)
class TemplateContract:
    """Machine-readable contract exported from an inspected template."""

    contract_version: str
    template_id: str
    template_label: str
    template_source: str
    title_slide: TemplateSectionContract
    contents_slide: TemplateSectionContract
    slide_patterns: tuple[TemplatePatternContract, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_contract": {
                "contract_version": self.contract_version,
                "template_id": self.template_id,
                "template_label": self.template_label,
                "template_source": self.template_source,
                "title_slide": self.title_slide.to_dict(),
                "contents_slide": self.contents_slide.to_dict(),
                "slide_patterns": [
                    pattern.to_dict() for pattern in self.slide_patterns
                ],
            }
        }


@dataclass(slots=True)
class MetricItem:
    """One user-facing metric row for a metrics slide."""

    label: str
    value: int

    def as_text(self) -> str:
        return f"{self.label}: {self.value}"


@dataclass(slots=True)
class ImageSpec:
    """One image input definition for a text-image slide or slot override."""

    path: Path | None = None
    ref: str | None = None
    fit: str = "contain"


@dataclass(slots=True)
class SlotOverride:
    """One exact-slot replacement payload."""

    slot_id: str
    text: list[str] | None = None
    image: ImageSpec | None = None


@dataclass(slots=True)
class PayloadSlide:
    """One authoring-friendly slide definition inside a report payload."""

    kind: str
    title: str
    include_in_contents: bool = True
    pattern_id: str | None = None
    body: list[str] = field(default_factory=list)
    items: list[MetricItem] = field(default_factory=list)
    image: ImageSpec | None = None
    caption: str | None = None
    slot_overrides: dict[str, SlotOverride] = field(default_factory=dict)


@dataclass(slots=True)
class TitleSlidePayload:
    """Opening slide payload."""

    title: str
    subtitle: list[str]


@dataclass(slots=True)
class ContentsSettings:
    """Controls whether an auto-generated contents slide is inserted."""

    enabled: bool = True


@dataclass(slots=True)
class ReportPayload:
    """Validated public payload used by the contract-first engine."""

    payload_version: str
    template_id: str
    title_slide: TitleSlidePayload
    contents: ContentsSettings
    slides: list[PayloadSlide]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_payload": {
                "payload_version": self.payload_version,
                "template_id": self.template_id,
                "title_slide": {
                    "title": self.title_slide.title,
                    "subtitle": list(self.title_slide.subtitle),
                },
                "contents": {
                    "enabled": self.contents.enabled,
                },
                "slides": [
                    _payload_slide_to_dict(slide) for slide in self.slides
                ],
            }
        }


def _payload_slide_to_dict(slide: PayloadSlide) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": slide.kind,
        "title": slide.title,
        "include_in_contents": slide.include_in_contents,
    }
    if slide.pattern_id is not None:
        payload["pattern_id"] = slide.pattern_id
    if slide.body:
        payload["body"] = list(slide.body)
    if slide.items:
        payload["items"] = [
            {"label": item.label, "value": item.value}
            for item in slide.items
        ]
    if slide.image is not None:
        image_payload: dict[str, Any] = {"fit": slide.image.fit}
        if slide.image.path is not None:
            image_payload["path"] = str(slide.image.path)
        if slide.image.ref is not None:
            image_payload["ref"] = slide.image.ref
        payload["image"] = image_payload
    if slide.caption is not None:
        payload["caption"] = slide.caption
    payload["slot_overrides"] = {
        slot_id: _slot_override_to_dict(override)
        for slot_id, override in slide.slot_overrides.items()
    }
    return payload


def _slot_override_to_dict(override: SlotOverride) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if override.text is not None:
        payload["text"] = (
            override.text[0]
            if len(override.text) == 1
            else list(override.text)
        )
    if override.image is not None:
        image_payload: dict[str, Any] = {"fit": override.image.fit}
        if override.image.path is not None:
            image_payload["path"] = str(override.image.path)
        if override.image.ref is not None:
            image_payload["ref"] = override.image.ref
        payload["image"] = image_payload
    return payload
