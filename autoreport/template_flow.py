"""Shared contract-export, authoring compile, and payload-scaffold helpers."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from autoreport.loader import load_yaml
from autoreport.models import (
    AUTHORING_PAYLOAD_VERSION,
    AuthoringPayload,
    AuthoringSlide,
    AuthoringSlideAssets,
    AuthoringSlideContext,
    ContentsSettings,
    DeckContext,
    ImageSpec,
    LayoutRequest,
    MetricItem,
    PayloadSlide,
    ReportPayload,
    REPORT_PAYLOAD_VERSION,
    SlotOverride,
    TemplateContract,
    TemplatePatternContract,
    TitleSlidePayload,
)
from autoreport.outputs.pptx_writer import PowerPointWriter
from autoreport.templates.weekly_report import (
    BASIC_TEMPLATE_NAME,
    export_template_contract,
    profile_template,
)
from autoreport.validator import (
    validate_authoring_payload,
    validate_payload,
    validate_template_contract,
)


PUBLIC_BUILT_IN_TEMPLATE_NAME = BASIC_TEMPLATE_NAME


@lru_cache(maxsize=1)
def get_built_in_profile():
    """Return the cached built-in editorial template profile."""

    writer = PowerPointWriter()
    presentation = writer._load_presentation(None)
    return profile_template(
        presentation,
        template_path=None,
        template_name=PUBLIC_BUILT_IN_TEMPLATE_NAME,
    )


@lru_cache(maxsize=1)
def get_built_in_contract() -> TemplateContract:
    """Return the cached built-in editorial public contract."""

    return export_template_contract(get_built_in_profile())


def inspect_template_contract(
    *,
    template_path: Path | None = None,
    built_in: str | None = None,
) -> TemplateContract:
    """Inspect a built-in or user-supplied template and export its contract."""

    if built_in == PUBLIC_BUILT_IN_TEMPLATE_NAME or (
        built_in is None and template_path is None
    ):
        return get_built_in_contract()

    if template_path is None:
        raise ValueError(
            f"Unsupported built-in template: {built_in} "
            f"(supported: {PUBLIC_BUILT_IN_TEMPLATE_NAME})"
        )

    writer = PowerPointWriter()
    presentation = writer._load_presentation(template_path)
    profile = profile_template(
        presentation,
        template_path=template_path,
        template_name=PUBLIC_BUILT_IN_TEMPLATE_NAME,
    )
    return export_template_contract(profile)


def scaffold_payload(
    contract: TemplateContract,
    *,
    include_text_image: bool = False,
) -> AuthoringPayload:
    """Return a starter authoring payload for a validated template contract."""

    slides: list[AuthoringSlide] = []

    if _find_first_pattern(contract, kind="text") is not None:
        slides.append(
            AuthoringSlide(
                slide_no=len(slides) + 1,
                goal="What It Does",
                context=AuthoringSlideContext(
                    summary="Generate editable PowerPoint decks from structured inputs.",
                    bullets=[
                        "Describe the slide goal and supporting bullets instead of drawing placeholder geometry.",
                        "The compiler resolves this authoring block into the runtime report payload automatically.",
                    ],
                ),
                assets=AuthoringSlideAssets(),
                layout_request=LayoutRequest(kind="text"),
            )
        )

    if _find_first_pattern(contract, kind="metrics") is not None:
        slides.append(
            AuthoringSlide(
                slide_no=len(slides) + 1,
                goal="Adoption Snapshot",
                context=AuthoringSlideContext(
                    metrics=[
                        MetricItem(label="Templates profiled", value=12),
                        MetricItem(label="Decks generated", value=24),
                    ]
                ),
                assets=AuthoringSlideAssets(),
                layout_request=LayoutRequest(kind="metrics"),
            )
        )

    if (
        include_text_image
        and _find_first_pattern(contract, kind="text_image", image_count=1) is not None
    ):
        slides.append(
            AuthoringSlide(
                slide_no=len(slides) + 1,
                goal="Why It Matters",
                context=AuthoringSlideContext(
                    summary="Pair narrative context with an uploaded image or a local file path.",
                    bullets=[
                        "Use assets.images[*].ref for web uploads.",
                        "Use assets.images[*].path when driving generation from the CLI.",
                    ],
                    caption="Example uses image_1 as the uploaded image ref.",
                ),
                assets=AuthoringSlideAssets(
                    images=[ImageSpec(ref="image_1", fit="contain")]
                ),
                layout_request=LayoutRequest(kind="text_image"),
            )
        )

    return AuthoringPayload(
        payload_version=AUTHORING_PAYLOAD_VERSION,
        template_id=contract.template_id,
        deck_context=DeckContext(
            audience="internal stakeholders",
            tone="concise",
            objective="weekly progress review",
        ),
        title_slide=TitleSlidePayload(
            title="Autoreport",
            subtitle=["Template-aware PPTX autofill engine"],
        ),
        contents=ContentsSettings(enabled=True),
        slides=slides,
    )


def scaffold_report_payload(contract: TemplateContract) -> ReportPayload:
    """Return a starter runtime payload for debugging and compatibility flows."""

    return compile_authoring_payload(
        scaffold_payload(contract, include_text_image=False),
        contract,
    )


def compile_authoring_payload(
    payload: AuthoringPayload,
    contract: TemplateContract,
) -> ReportPayload:
    """Compile a validated authoring payload into the runtime report payload."""

    compiled_slides: list[PayloadSlide] = []
    for slide in payload.slides:
        pattern = _select_authoring_pattern(contract, slide)
        body_lines = _build_body_lines(slide.context)
        slot_overrides: dict[str, SlotOverride] = {}
        runtime_image: ImageSpec | None = None
        runtime_caption: str | None = None

        if slide.layout_request is not None and slide.layout_request.kind == "text_image":
            image_count = _pattern_image_count(pattern)
            if image_count <= 1:
                runtime_image = slide.assets.images[0]
                runtime_caption = slide.context.caption
            else:
                for index, image in enumerate(slide.assets.images, start=1):
                    slot_overrides[f"text_image.image_{index}"] = SlotOverride(
                        slot_id=f"text_image.image_{index}",
                        image=image,
                    )
                if slide.context.caption:
                    slot_overrides["text_image.caption_1"] = SlotOverride(
                        slot_id="text_image.caption_1",
                        text=[slide.context.caption],
                    )

        compiled_slides.append(
            PayloadSlide(
                kind=slide.layout_request.kind if slide.layout_request else "text",
                title=slide.goal,
                include_in_contents=slide.include_in_contents,
                pattern_id=pattern.pattern_id,
                body=body_lines,
                items=list(slide.context.metrics),
                image=runtime_image,
                caption=runtime_caption,
                slot_overrides=slot_overrides,
            )
        )

    return ReportPayload(
        payload_version=REPORT_PAYLOAD_VERSION,
        template_id=payload.template_id,
        title_slide=payload.title_slide,
        contents=payload.contents,
        slides=compiled_slides,
    )


def materialize_report_payload(
    raw_data: dict[str, Any],
    contract: TemplateContract,
    *,
    available_image_refs: Iterable[str] = (),
) -> ReportPayload:
    """Validate incoming authoring/runtime content and return a runtime payload."""

    payload_kind = detect_payload_kind(raw_data)
    if payload_kind == "authoring":
        authoring_payload = validate_authoring_payload(
            raw_data,
            contract,
            available_image_refs=available_image_refs,
        )
        return compile_authoring_payload(authoring_payload, contract)

    return validate_payload(
        raw_data,
        contract,
        available_image_refs=available_image_refs,
    )


def detect_payload_kind(raw_data: dict[str, Any]) -> str:
    """Infer whether a payload mapping is authoring or runtime shaped."""

    if "authoring_payload" in raw_data:
        return "authoring"
    if "report_payload" in raw_data:
        return "report"
    if "deck_context" in raw_data:
        return "authoring"

    slides = raw_data.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            if any(key in slide for key in {"slide_no", "goal", "layout_request"}):
                return "authoring"

    return "report"


def load_template_contract(path: Path) -> TemplateContract:
    """Load and validate a contract file from disk."""

    raw = load_yaml(path)
    return validate_template_contract(raw)


def serialize_document(document: dict[str, Any], *, fmt: str) -> str:
    """Serialize a wrapped YAML/JSON document for CLI or web display."""

    if fmt == "json":
        return json.dumps(document, indent=2)
    return yaml.safe_dump(
        document,
        sort_keys=False,
        allow_unicode=True,
    )


def _build_body_lines(context: AuthoringSlideContext) -> list[str]:
    lines: list[str] = []
    if context.summary is not None:
        lines.append(context.summary)
    lines.extend(context.bullets)
    return lines


def _select_authoring_pattern(
    contract: TemplateContract,
    slide: AuthoringSlide,
) -> TemplatePatternContract:
    if slide.layout_request is None:
        raise ValueError("Authoring slide is missing layout_request.")

    requested_count = (
        slide.layout_request.image_count
        if slide.layout_request.image_count is not None
        else len(slide.assets.images)
    )
    if slide.layout_request.kind != "text_image":
        requested_count = 0

    candidates = [
        pattern
        for pattern in contract.slide_patterns
        if pattern.kind == slide.layout_request.kind
    ]
    if not candidates:
        raise ValueError(
            f"Template '{contract.template_id}' does not support kind "
            f"'{slide.layout_request.kind}'."
        )

    if slide.layout_request.pattern_id is not None:
        for pattern in candidates:
            if pattern.pattern_id == slide.layout_request.pattern_id:
                return pattern
        raise ValueError(
            f"Pattern '{slide.layout_request.pattern_id}' is not valid for kind "
            f"'{slide.layout_request.kind}'."
        )

    for pattern in candidates:
        if _pattern_image_count(pattern) != requested_count:
            continue
        if slide.layout_request.image_orientation != "auto":
            if _pattern_image_layout(pattern) != slide.layout_request.image_orientation:
                continue
        return pattern

    raise ValueError(
        f"Template '{contract.template_id}' does not define a pattern for kind "
        f"'{slide.layout_request.kind}' with image_count={requested_count} "
        f"and image_orientation='{slide.layout_request.image_orientation}'."
    )


def _find_first_pattern(
    contract: TemplateContract,
    *,
    kind: str,
    image_count: int | None = None,
    image_layout: str | None = None,
) -> TemplatePatternContract | None:
    for pattern in contract.slide_patterns:
        if pattern.kind != kind:
            continue
        if image_count is not None and _pattern_image_count(pattern) != image_count:
            continue
        if image_layout is not None and _pattern_image_layout(pattern) != image_layout:
            continue
        return pattern
    return None


def _pattern_image_count(pattern: TemplatePatternContract) -> int:
    if pattern.image_count is not None:
        return pattern.image_count
    return sum(1 for slot in pattern.slots if slot.slot_type == "image")


def _pattern_image_layout(pattern: TemplatePatternContract) -> str:
    if pattern.image_layout is not None:
        return pattern.image_layout
    image_slots = [slot for slot in pattern.slots if slot.slot_type == "image"]
    if not image_slots:
        return "stack"
    return image_slots[0].orientation or "stack"
