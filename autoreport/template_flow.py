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
    ValidationError,
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


def materialize_authoring_payload(
    raw_data: dict[str, Any],
    contract: TemplateContract,
    *,
    available_image_refs: Iterable[str] = (),
    enforce_image_refs: bool = True,
) -> tuple[AuthoringPayload, list[str]]:
    """Normalize supported draft inputs into an authoring payload."""

    payload_kind = detect_payload_kind(raw_data)
    if payload_kind == "authoring":
        return (
            validate_authoring_payload(
                raw_data,
                contract,
                available_image_refs=available_image_refs,
                enforce_image_refs=enforce_image_refs,
            ),
            [],
        )
    if payload_kind == "content":
        return _normalize_report_content(
            raw_data,
            contract,
            available_image_refs=available_image_refs,
            enforce_image_refs=enforce_image_refs,
        )
    raise ValueError(
        "Only authoring_payload or report_content can be normalized into authoring_payload."
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
    enforce_image_refs: bool = True,
) -> ReportPayload:
    """Validate incoming authoring/runtime content and return a runtime payload."""

    payload_kind = detect_payload_kind(raw_data)
    if payload_kind in {"authoring", "content"}:
        authoring_payload, _ = materialize_authoring_payload(
            raw_data,
            contract,
            available_image_refs=available_image_refs,
            enforce_image_refs=enforce_image_refs,
        )
        return compile_authoring_payload(authoring_payload, contract)

    return validate_payload(
        raw_data,
        contract,
        available_image_refs=available_image_refs,
        enforce_image_refs=enforce_image_refs,
    )


def detect_payload_kind(raw_data: dict[str, Any]) -> str:
    """Infer whether a payload mapping is authoring or runtime shaped."""

    if "authoring_payload" in raw_data:
        return "authoring"
    if "report_content" in raw_data:
        return "content"
    if "report_payload" in raw_data:
        return "report"
    if "deck_context" in raw_data:
        return "authoring"

    if isinstance(raw_data.get("title_slide"), dict):
        title_slide = raw_data["title_slide"]
        if isinstance(title_slide.get("slots"), dict):
            return "content"

    slides = raw_data.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            if any(key in slide for key in {"slide_no", "goal", "layout_request"}):
                return "authoring"
            if "slots" in slide:
                return "content"

    return "report"


def _normalize_report_content(
    raw_data: dict[str, Any],
    contract: TemplateContract,
    *,
    available_image_refs: Iterable[str] = (),
    enforce_image_refs: bool = True,
) -> tuple[AuthoringPayload, list[str]]:
    root = _unwrap_report_content(raw_data)
    errors: list[str] = []
    hints: list[str] = []

    if not isinstance(root, dict):
        raise ValidationError(
            ["Report content must be a YAML mapping under the 'report_content' key."]
        )

    provided_template_id = root.get("template_id")
    if isinstance(provided_template_id, str):
        provided_template_id = provided_template_id.strip()
    if provided_template_id and provided_template_id != contract.template_id:
        errors.append(f"Field 'template_id' must match '{contract.template_id}'.")

    title_slide = root.get("title_slide")
    if not isinstance(title_slide, dict):
        errors.append("Field 'title_slide' is required.")
        title_value = "Autoreport"
        subtitle_lines = ["Template-aware PPTX autofill engine"]
    else:
        title_slots = title_slide.get("slots")
        if not isinstance(title_slots, dict):
            errors.append("Field 'title_slide.slots' must be an object.")
            title_value = "Autoreport"
            subtitle_lines = ["Template-aware PPTX autofill engine"]
        else:
            title_value = _normalize_scalar_slot(
                title_slots.get("title"),
                fallback="Autoreport",
            )
            subtitle_lines = _split_text_lines(title_slots.get("subtitle_1"))
            if not subtitle_lines:
                subtitle_lines = ["Template-aware PPTX autofill engine"]

    contents_enabled = isinstance(root.get("contents_slide"), dict)

    raw_slides = root.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        errors.append("Field 'slides' must contain at least 1 item.")
        raw_slides = []

    slides: list[AuthoringSlide] = []
    for index, raw_slide in enumerate(raw_slides, start=1):
        normalized = _normalize_report_content_slide(
            raw_slide,
            slide_no=index,
            contract=contract,
            available_image_refs=tuple(available_image_refs),
            hints=hints,
            errors=errors,
        )
        if normalized is not None:
            slides.append(normalized)

    if errors:
        raise ValidationError(errors)

    authoring_payload = AuthoringPayload(
        payload_version=AUTHORING_PAYLOAD_VERSION,
        template_id=contract.template_id,
        deck_context=DeckContext(),
        title_slide=TitleSlidePayload(
            title=title_value,
            subtitle=subtitle_lines,
        ),
        contents=ContentsSettings(enabled=contents_enabled),
        slides=slides,
    )

    validated = validate_authoring_payload(
        authoring_payload.to_dict(),
        contract,
        available_image_refs=available_image_refs,
        enforce_image_refs=enforce_image_refs,
    )
    return validated, hints


def _normalize_report_content_slide(
    raw_slide: Any,
    *,
    slide_no: int,
    contract: TemplateContract,
    available_image_refs: Iterable[str],
    hints: list[str],
    errors: list[str],
) -> AuthoringSlide | None:
    prefix = f"slides[{slide_no - 1}]"
    if not isinstance(raw_slide, dict):
        errors.append(f"Field '{prefix}' must be an object.")
        return None

    pattern_id = _optional_string(raw_slide.get("pattern_id"))
    kind = _optional_string(raw_slide.get("kind")) or _infer_kind_from_pattern(
        contract,
        pattern_id,
    )
    if kind not in {"text", "metrics", "text_image"}:
        errors.append(
            f"Field '{prefix}.kind' must be one of 'text', 'metrics', or 'text_image'."
        )
        return None

    slots = raw_slide.get("slots")
    if not isinstance(slots, dict):
        errors.append(f"Field '{prefix}.slots' must be an object.")
        return None

    goal = _normalize_scalar_slot(slots.get("title"), fallback=f"Slide {slide_no}")
    body_text = _normalize_multiline_text(slots.get("body_1"))
    caption = _optional_string(slots.get("caption_1"))
    images, image_notes = _normalize_report_content_images(
        slots,
        available_image_refs=available_image_refs,
    )
    for note in image_notes:
        hints.append(f"Slide {slide_no}: {note}")

    if kind == "metrics":
        context = AuthoringSlideContext(
            metrics=_parse_metric_items(body_text),
        )
    else:
        bullets = [
            f"Image request note: {note}"
            for note in image_notes
        ]
        context = AuthoringSlideContext(
            summary=body_text,
            bullets=bullets,
            caption=caption,
        )

    layout_request = LayoutRequest(
        kind=kind,
        pattern_id=pattern_id,
        image_count=(len(images) if kind == "text_image" else None),
        image_orientation=(
            _pattern_image_layout(_lookup_pattern(contract, pattern_id))
            if kind == "text_image" and pattern_id is not None and _lookup_pattern(contract, pattern_id) is not None
            else "auto"
        ),
    )

    return AuthoringSlide(
        slide_no=slide_no,
        goal=goal,
        include_in_contents=True,
        context=context,
        assets=AuthoringSlideAssets(images=images if kind == "text_image" else []),
        layout_request=layout_request,
    )


def _normalize_report_content_images(
    slots: dict[str, Any],
    *,
    available_image_refs: Iterable[str],
) -> tuple[list[ImageSpec], list[str]]:
    images: list[ImageSpec] = []
    notes: list[str] = []
    available_ref_set = set(available_image_refs)

    image_aliases = sorted(
        alias
        for alias in slots
        if isinstance(alias, str) and alias.startswith("image_")
    )
    for alias in image_aliases:
        raw_value = slots.get(alias)
        normalized = _optional_string(raw_value)
        if normalized is None:
            images.append(ImageSpec(ref=alias, fit="contain"))
            continue

        looks_like_path = any(token in normalized for token in ("\\", "/")) or normalized.lower().endswith(
            (".png", ".jpg", ".jpeg")
        )
        if normalized in available_ref_set or normalized == alias:
            images.append(ImageSpec(ref=normalized, fit="contain"))
            continue
        if looks_like_path:
            images.append(ImageSpec(path=Path(normalized), fit="contain"))
            continue

        images.append(ImageSpec(ref=alias, fit="contain"))
        notes.append(f"{alias} should later be replaced with a real uploaded image. Draft note: {normalized}")

    return images, notes


def _parse_metric_items(body_text: str | None) -> list[MetricItem]:
    if not body_text:
        return [MetricItem(label="Key metric", value="Add the metric value.")]

    items: list[MetricItem] = []
    for line in body_text.splitlines():
        normalized = line.strip().lstrip("-").lstrip("•").strip()
        if not normalized:
            continue
        if ":" in normalized:
            label, value = normalized.split(":", 1)
            items.append(
                MetricItem(
                    label=label.strip() or "Metric",
                    value=value.strip() or "n/a",
                )
            )
            continue
        items.append(MetricItem(label=normalized, value="n/a"))

    return items or [MetricItem(label="Key metric", value="Add the metric value.")]


def _unwrap_report_content(raw_data: dict[str, Any]) -> dict[str, Any]:
    if "report_content" not in raw_data:
        return raw_data

    wrapped = raw_data.get("report_content")
    if not isinstance(wrapped, dict):
        raise ValidationError(
            ["Field 'report_content' must be a YAML mapping."]
        )
    return wrapped


def _lookup_pattern(
    contract: TemplateContract,
    pattern_id: str | None,
) -> TemplatePatternContract | None:
    if pattern_id is None:
        return None
    for pattern in contract.slide_patterns:
        if pattern.pattern_id == pattern_id:
            return pattern
    return None


def _infer_kind_from_pattern(
    contract: TemplateContract,
    pattern_id: str | None,
) -> str | None:
    pattern = _lookup_pattern(contract, pattern_id)
    if pattern is None:
        return None
    return pattern.kind


def _normalize_scalar_slot(raw: Any, *, fallback: str) -> str:
    normalized = _optional_string(raw)
    return fallback if normalized is None else normalized


def _normalize_multiline_text(raw: Any) -> str | None:
    normalized = _optional_string(raw)
    return normalized


def _split_text_lines(raw: Any) -> list[str]:
    normalized = _optional_string(raw)
    if normalized is None:
        return []
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _optional_string(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    normalized = raw.strip()
    if not normalized:
        return None
    return normalized


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
