"""Shared contract-export, authoring compile, and payload-scaffold helpers."""

from __future__ import annotations

from difflib import get_close_matches
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
    MANUAL_TEMPLATE_NAME,
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
SUPPORTED_BUILT_IN_TEMPLATE_NAMES = (
    BASIC_TEMPLATE_NAME,
    MANUAL_TEMPLATE_NAME,
)


@lru_cache(maxsize=4)
def get_built_in_profile(template_name: str = PUBLIC_BUILT_IN_TEMPLATE_NAME):
    """Return a cached built-in template profile."""

    writer = PowerPointWriter()
    presentation = writer._load_presentation(None)
    return profile_template(
        presentation,
        template_path=None,
        template_name=template_name,
    )


@lru_cache(maxsize=4)
def get_built_in_contract(
    template_name: str = PUBLIC_BUILT_IN_TEMPLATE_NAME,
) -> TemplateContract:
    """Return a cached built-in public contract."""

    return export_template_contract(get_built_in_profile(template_name))


def inspect_template_contract(
    *,
    template_path: Path | None = None,
    built_in: str | None = None,
) -> TemplateContract:
    """Inspect a built-in or user-supplied template and export its contract."""

    if built_in is None and template_path is None:
        return get_built_in_contract()
    if template_path is None and built_in in SUPPORTED_BUILT_IN_TEMPLATE_NAMES:
        return get_built_in_contract(built_in)

    if template_path is None:
        supported = ", ".join(SUPPORTED_BUILT_IN_TEMPLATE_NAMES)
        raise ValueError(
            f"Unsupported built-in template: {built_in} "
            f"(supported: {supported})"
        )

    writer = PowerPointWriter()
    presentation = writer._load_presentation(template_path)
    profile = profile_template(
        presentation,
        template_path=template_path,
        template_name=(built_in or PUBLIC_BUILT_IN_TEMPLATE_NAME),
    )
    return export_template_contract(profile)


def scaffold_payload(
    contract: TemplateContract,
    *,
    include_text_image: bool = False,
) -> AuthoringPayload:
    """Return a starter authoring payload for a validated template contract."""

    if contract.template_id == "autoreport-manual-v1":
        return _scaffold_manual_payload(contract)

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
        body_lines = _build_compiled_body_lines(slide, pattern)
        slot_overrides = _build_compiled_slot_overrides(slide, pattern)
        runtime_image, runtime_caption = _compile_text_image_runtime_media(
            slide,
            pattern,
            slot_overrides,
        )

        compiled_slides.append(
            PayloadSlide(
                kind=slide.layout_request.kind if slide.layout_request else "text",
                title=_derive_slide_title(slide, pattern),
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
        title_slide=TitleSlidePayload(
            title=payload.title_slide.title,
            subtitle=list(payload.title_slide.subtitle),
            slot_values=dict(payload.title_slide.slot_values),
        ),
        contents=ContentsSettings(
            enabled=payload.contents.enabled,
            slot_values=dict(payload.contents.slot_values),
        ),
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
        title_slot_values: dict[str, str] = {}
    else:
        title_slots = title_slide.get("slots")
        if not isinstance(title_slots, dict):
            errors.append("Field 'title_slide.slots' must be an object.")
            title_value = "Autoreport"
            subtitle_lines = ["Template-aware PPTX autofill engine"]
            title_slot_values = {}
        else:
            title_slot_values = _extract_named_slot_values(title_slots)
            title_value = _resolve_title_value_from_slot_values(
                title_slot_values,
                contract.title_slide,
                fallback="Autoreport",
            )
            subtitle_lines = _resolve_subtitle_lines_from_slot_values(
                title_slot_values,
                contract.title_slide,
                fallback=["Template-aware PPTX autofill engine"],
            )

    raw_contents_slide = root.get("contents_slide")
    contents_enabled = isinstance(raw_contents_slide, dict)
    contents_slot_values: dict[str, str] = {}
    if contents_enabled:
        raw_contents_slots = raw_contents_slide.get("slots")
        if not isinstance(raw_contents_slots, dict):
            errors.append("Field 'contents_slide.slots' must be an object.")
        else:
            contents_slot_values = _extract_named_slot_values(raw_contents_slots)

    raw_slides = root.get("slides")
    if not isinstance(raw_slides, list) or not raw_slides:
        errors.append("Field 'slides' must contain at least 1 item.")
        raw_slides = []

    slides: list[AuthoringSlide] = []
    next_generated_image_index = 1
    for index, raw_slide in enumerate(raw_slides, start=1):
        normalized, next_generated_image_index = _normalize_report_content_slide(
            raw_slide,
            slide_no=index,
            contract=contract,
            available_image_refs=tuple(available_image_refs),
            next_generated_image_index=next_generated_image_index,
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
            slot_values=title_slot_values,
        ),
        contents=ContentsSettings(
            enabled=contents_enabled,
            slot_values=contents_slot_values,
        ),
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
    next_generated_image_index: int,
    hints: list[str],
    errors: list[str],
) -> tuple[AuthoringSlide | None, int]:
    prefix = f"slides[{slide_no - 1}]"
    if not isinstance(raw_slide, dict):
        errors.append(f"Field '{prefix}' must be an object.")
        return None, next_generated_image_index

    pattern_id = _optional_string(raw_slide.get("pattern_id"))
    pattern = _lookup_pattern(contract, pattern_id)
    if pattern is None and pattern_id is not None:
        repaired_pattern = _repair_report_content_pattern(contract, pattern_id)
        if repaired_pattern is not None:
            hints.append(
                f"Slide {slide_no}: pattern_id '{pattern_id}' was expanded to "
                f"'{repaired_pattern.pattern_id}' from the template contract."
            )
            pattern = repaired_pattern
            pattern_id = repaired_pattern.pattern_id
    if pattern_id is not None and pattern is None:
        errors.append(
            _build_unknown_report_content_pattern_error(
                contract=contract,
                prefix=prefix,
                pattern_id=pattern_id,
            )
        )
        return None, next_generated_image_index

    slots = raw_slide.get("slots")
    if not isinstance(slots, dict):
        errors.append(f"Field '{prefix}.slots' must be an object.")
        return None, next_generated_image_index

    kind = _infer_report_content_kind(
        contract,
        raw_slide=raw_slide,
        pattern=pattern,
        slots=slots,
    )
    if kind is None:
        errors.append(
            f"Field '{prefix}' needs a valid pattern_id or enough slide structure "
            "for Autoreport to infer a supported template pattern."
        )
        return None, next_generated_image_index

    slot_values = _extract_named_slot_values(slots, skip_prefixes=("image_",))
    goal = _derive_goal_from_slot_values(
        slot_values=slot_values,
        pattern=pattern,
        fallback=f"Slide {slide_no}",
    )
    body_text = _resolve_body_text_from_slot_values(slot_values, pattern)
    caption = _resolve_primary_caption_from_slot_values(slot_values)
    images, image_notes, next_generated_image_index = _normalize_report_content_images(
        slots,
        available_image_refs=available_image_refs,
        next_generated_image_index=next_generated_image_index,
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
            _pattern_image_layout(pattern)
            if kind == "text_image" and pattern is not None
            else "auto"
        ),
    )

    return (
        AuthoringSlide(
            slide_no=slide_no,
            goal=goal,
            include_in_contents=True,
            context=context,
            assets=AuthoringSlideAssets(images=images if kind == "text_image" else []),
            layout_request=layout_request,
            slot_values=slot_values,
        ),
        next_generated_image_index,
    )


def _normalize_report_content_images(
    slots: dict[str, Any],
    *,
    available_image_refs: Iterable[str],
    next_generated_image_index: int,
) -> tuple[list[ImageSpec], list[str], int]:
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
            generated_ref = f"image_{next_generated_image_index}"
            images.append(ImageSpec(ref=generated_ref, fit="contain"))
            notes.append(
                f"{alias} was mapped to upload ref '{generated_ref}'. Upload a real image file for that ref later."
            )
            next_generated_image_index += 1
            continue

        looks_like_path = any(token in normalized for token in ("\\", "/")) or normalized.lower().endswith(
            (".png", ".jpg", ".jpeg")
        )
        if (
            normalized in available_ref_set
            or normalized == alias
            or (
                normalized.startswith("image_")
                and normalized.removeprefix("image_").isdigit()
            )
        ):
            images.append(ImageSpec(ref=normalized, fit="contain"))
            continue
        if looks_like_path:
            images.append(ImageSpec(path=Path(normalized), fit="contain"))
            continue

        generated_ref = f"image_{next_generated_image_index}"
        images.append(ImageSpec(ref=generated_ref, fit="contain"))
        notes.append(
            f"{alias} was mapped to upload ref '{generated_ref}'. Draft note: {normalized}. Upload a matching image for that ref later."
        )
        next_generated_image_index += 1

    return images, notes, next_generated_image_index


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


def _repair_report_content_pattern(
    contract: TemplateContract,
    pattern_id: str,
) -> TemplatePatternContract | None:
    prefix_matches = [
        pattern
        for pattern in contract.slide_patterns
        if pattern.pattern_id.startswith(pattern_id)
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if prefix_matches:
        shortest_match = min(prefix_matches, key=lambda pattern: len(pattern.pattern_id))
        if all(
            match.pattern_id.startswith(shortest_match.pattern_id)
            for match in prefix_matches
        ):
            return shortest_match
    return None


def _build_unknown_report_content_pattern_error(
    *,
    contract: TemplateContract,
    prefix: str,
    pattern_id: str,
) -> str:
    known_pattern_ids = [pattern.pattern_id for pattern in contract.slide_patterns]
    close_matches = get_close_matches(pattern_id, known_pattern_ids, n=3, cutoff=0.55)
    if close_matches:
        formatted = ", ".join(f"'{match}'" for match in close_matches)
        return (
            f"Field '{prefix}.pattern_id' must match a template pattern from the "
            f"contract. Got '{pattern_id}'. Closest matches: {formatted}."
        )
    return (
        f"Field '{prefix}.pattern_id' must match a template pattern from the "
        f"contract. Got '{pattern_id}'."
    )


def _infer_report_content_kind(
    contract: TemplateContract,
    *,
    raw_slide: dict[str, Any],
    pattern: TemplatePatternContract | None,
    slots: dict[str, Any],
) -> str | None:
    if pattern is not None:
        return pattern.kind

    supported_kinds = {
        candidate.kind for candidate in contract.slide_patterns if candidate.kind
    }
    raw_kind = _optional_string(raw_slide.get("kind"))
    if raw_kind in supported_kinds:
        return raw_kind

    image_alias_count = sum(
        1
        for alias in slots
        if isinstance(alias, str) and alias.startswith("image_")
    )
    if image_alias_count > 0 and "text_image" in supported_kinds:
        return "text_image"

    if _looks_like_metrics_body(slots) and "metrics" in supported_kinds:
        return "metrics"

    if "text" in supported_kinds:
        return "text"

    if len(supported_kinds) == 1:
        return next(iter(supported_kinds))

    return None


def _looks_like_metrics_body(slots: dict[str, Any]) -> bool:
    body_text = _normalize_multiline_text(slots.get("body_1"))
    if body_text is None:
        return False

    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False

    metric_like_lines = 0
    for line in lines:
        normalized = line.lstrip("-").lstrip("•").strip()
        if ":" in normalized:
            metric_like_lines += 1
    return metric_like_lines == len(lines)


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


def _scaffold_manual_payload(contract: TemplateContract) -> AuthoringPayload:
    return AuthoringPayload(
        payload_version=AUTHORING_PAYLOAD_VERSION,
        template_id=contract.template_id,
        deck_context=DeckContext(
            audience="customers",
            tone="instructional",
            objective="customer walkthrough for starter templates and PowerPoint generation",
        ),
        title_slide=TitleSlidePayload(
            title="Autoreport PowerPoint User Guide",
            subtitle=[
                "Screenshot-first user guide",
                "v0.4",
                "Autoreport Team",
            ],
            slot_values={
                "doc_title": "Autoreport PowerPoint User Guide",
                "doc_subtitle": "Screenshot-first user guide",
                "doc_version": "v0.4",
                "author_or_owner": "Autoreport Team",
            },
        ),
        contents=ContentsSettings(
            enabled=True,
            slot_values={
                "contents_title": "Contents",
                "contents_group_label": "Procedure Overview",
            },
        ),
        slides=[
            AuthoringSlide(
                slide_no=1,
                goal="1. Choose A Starter Template",
                context=AuthoringSlideContext(),
                assets=AuthoringSlideAssets(),
                layout_request=LayoutRequest(
                    kind="text",
                    pattern_id="text.manual.section_break",
                ),
                slot_values={
                    "section_no": "1.",
                    "section_title": "Choose A Starter Template",
                    "section_subtitle": "Start with the built-in editorial or manual starter before editing content.",
                },
            ),
            AuthoringSlide(
                slide_no=2,
                goal="1.1 Review The Starter Example",
                context=AuthoringSlideContext(
                    summary="Open the starter example and confirm the selected template."
                ),
                assets=AuthoringSlideAssets(
                    images=[ImageSpec(ref="image_1", fit="contain")]
                ),
                layout_request=LayoutRequest(
                    kind="text_image",
                    pattern_id="text_image.manual.procedure.one",
                    image_count=1,
                ),
                slot_values={
                    "step_no": "1.1",
                    "step_title": "Review The Starter Example",
                    "command_or_action": "Action: open the starter example and confirm the selected template.",
                    "summary": "Use one screenshot to show the starting editor state.",
                    "detail_body": "Review the starter YAML, note the built-in template mode, and confirm the page is ready before moving to the next step.",
                    "caption_1": "Starter example loaded in the editor",
                },
            ),
            AuthoringSlide(
                slide_no=3,
                goal="1.2 Customize The Draft",
                context=AuthoringSlideContext(
                    summary="Capture the starter draft before and after the edits."
                ),
                assets=AuthoringSlideAssets(
                    images=[
                        ImageSpec(ref="image_2", fit="contain"),
                        ImageSpec(ref="image_3", fit="contain"),
                    ]
                ),
                layout_request=LayoutRequest(
                    kind="text_image",
                    pattern_id="text_image.manual.procedure.two",
                    image_count=2,
                ),
                slot_values={
                    "step_no": "1.2",
                    "step_title": "Customize The Draft",
                    "command_or_action": "Action: edit the YAML title, sections, and example copy.",
                    "summary": "Use the ordered screenshots to compare the starter draft before and after the edits.",
                    "detail_body": "Update the guide title and slide text, then compare the edited YAML against the original starter so the customer can see what changed.",
                    "caption_1": "Starter YAML before editing",
                    "caption_2": "Starter YAML after editing",
                },
            ),
            AuthoringSlide(
                slide_no=4,
                goal="1.3 Generate The PowerPoint",
                context=AuthoringSlideContext(
                    summary="Show the preview, generation, and download checkpoints."
                ),
                assets=AuthoringSlideAssets(
                    images=[
                        ImageSpec(ref="image_4", fit="contain"),
                        ImageSpec(ref="image_5", fit="contain"),
                        ImageSpec(ref="image_6", fit="contain"),
                    ]
                ),
                layout_request=LayoutRequest(
                    kind="text_image",
                    pattern_id="text_image.manual.procedure.three",
                    image_count=3,
                ),
                slot_values={
                    "step_no": "1.3",
                    "step_title": "Generate The PowerPoint",
                    "command_or_action": "Action: refresh the slide order and generate the PowerPoint deck.",
                    "summary": "Use three screenshots to document preview, generation, and download.",
                    "detail_body": "Refresh the manual slide order, confirm the PowerPoint preview, and generate the deck so the download step is visible end to end.",
                    "caption_1": "Slide preview ready",
                    "caption_2": "Generation in progress",
                    "caption_3": "PowerPoint download complete",
                },
            ),
        ],
    )


def _extract_named_slot_values(
    slots: dict[str, Any],
    *,
    skip_prefixes: tuple[str, ...] = (),
) -> dict[str, str]:
    values: dict[str, str] = {}
    for alias, raw_value in slots.items():
        if not isinstance(alias, str):
            continue
        if any(alias.startswith(prefix) for prefix in skip_prefixes):
            continue
        normalized = _normalize_named_slot_value(raw_value)
        if normalized is not None:
            values[alias] = normalized
    return values


def _normalize_named_slot_value(raw_value: Any) -> str | None:
    normalized = _optional_string(raw_value)
    if normalized is not None:
        return normalized
    if isinstance(raw_value, bool):
        return "true" if raw_value else "false"
    if isinstance(raw_value, int):
        return str(raw_value)
    if isinstance(raw_value, float):
        if raw_value.is_integer():
            return f"{int(raw_value)}."
        return format(raw_value, "g")
    return None


def _resolve_title_value_from_slot_values(
    slot_values: dict[str, str],
    section,
    *,
    fallback: str,
) -> str:
    title_alias = _section_title_alias(section)
    if title_alias is not None and title_alias in slot_values:
        return slot_values[title_alias]
    return fallback


def _resolve_subtitle_lines_from_slot_values(
    slot_values: dict[str, str],
    section,
    *,
    fallback: list[str],
) -> list[str]:
    lines: list[str] = []
    for slot in _ordered_text_slots(section):
        alias = slot.alias
        if alias in slot_values:
            lines.extend(_split_text_lines(slot_values[alias]))
    return lines or fallback


def _derive_goal_from_slot_values(
    *,
    slot_values: dict[str, str],
    pattern: TemplatePatternContract | None,
    fallback: str,
) -> str:
    if "section_no" in slot_values and "section_title" in slot_values:
        return _join_title_parts(slot_values["section_no"], slot_values["section_title"])
    if "step_no" in slot_values and "step_title" in slot_values:
        return _join_title_parts(slot_values["step_no"], slot_values["step_title"])
    title_alias = _pattern_title_alias(pattern)
    if title_alias is not None and title_alias in slot_values:
        return slot_values[title_alias]
    return fallback


def _resolve_body_text_from_slot_values(
    slot_values: dict[str, str],
    pattern: TemplatePatternContract | None,
) -> str | None:
    for alias in _pattern_body_aliases(pattern):
        if alias in slot_values:
            return slot_values[alias]
    return None


def _resolve_primary_caption_from_slot_values(
    slot_values: dict[str, str],
) -> str | None:
    return slot_values.get("caption_1")


def _build_compiled_body_lines(
    slide: AuthoringSlide,
    pattern: TemplatePatternContract,
) -> list[str]:
    for alias in _pattern_body_aliases(pattern):
        if alias in slide.slot_values:
            return [
                line.strip()
                for line in slide.slot_values[alias].splitlines()
                if line.strip()
            ] or [slide.slot_values[alias]]
    return _build_body_lines(slide.context)


def _build_compiled_slot_overrides(
    slide: AuthoringSlide,
    pattern: TemplatePatternContract,
) -> dict[str, SlotOverride]:
    slot_overrides: dict[str, SlotOverride] = {}
    body_aliases = _pattern_body_aliases(pattern)
    alias_to_slot_id = {
        slot.alias: slot.slot_id
        for slot in pattern.slots
        if slot.alias is not None and slot.slot_type != "image"
    }
    for alias, value in slide.slot_values.items():
        if alias in body_aliases:
            continue
        slot_id = alias_to_slot_id.get(alias)
        if slot_id is None:
            continue
        slot_overrides[slot_id] = SlotOverride(
            slot_id=slot_id,
            text=[value],
        )
    return slot_overrides


def _compile_text_image_runtime_media(
    slide: AuthoringSlide,
    pattern: TemplatePatternContract,
    slot_overrides: dict[str, SlotOverride],
) -> tuple[ImageSpec | None, str | None]:
    if slide.layout_request is None or slide.layout_request.kind != "text_image":
        return None, None

    image_slots = sorted(
        (slot for slot in pattern.slots if slot.slot_type == "image"),
        key=lambda slot: slot.order or 0,
    )
    caption_slots = sorted(
        (slot for slot in pattern.slots if slot.slot_type == "caption"),
        key=lambda slot: slot.order or 0,
    )
    if len(image_slots) <= 1:
        runtime_caption: str | None = None
        if caption_slots:
            primary_caption_alias = caption_slots[0].alias
            if primary_caption_alias and primary_caption_alias in slide.slot_values:
                runtime_caption = slide.slot_values[primary_caption_alias]
                slot_overrides.pop(caption_slots[0].slot_id, None)
            elif slide.context.caption:
                runtime_caption = slide.context.caption
        return (
            slide.assets.images[0] if slide.assets.images else None,
            runtime_caption,
        )

    for index, image in enumerate(slide.assets.images, start=1):
        slot_id = f"text_image.image_{index}"
        slot_overrides[slot_id] = SlotOverride(
            slot_id=slot_id,
            image=image,
        )
    for caption_slot in caption_slots:
        alias = caption_slot.alias
        if alias is not None and alias in slide.slot_values:
            slot_overrides[caption_slot.slot_id] = SlotOverride(
                slot_id=caption_slot.slot_id,
                text=[slide.slot_values[alias]],
            )
    if slide.context.caption and caption_slots and caption_slots[0].slot_id not in slot_overrides:
        slot_overrides[caption_slots[0].slot_id] = SlotOverride(
            slot_id=caption_slots[0].slot_id,
            text=[slide.context.caption],
        )
    return None, None


def _derive_slide_title(
    slide: AuthoringSlide,
    pattern: TemplatePatternContract,
) -> str:
    if "section_no" in slide.slot_values and "section_title" in slide.slot_values:
        return _join_title_parts(
            slide.slot_values["section_no"],
            slide.slot_values["section_title"],
        )
    if "step_no" in slide.slot_values and "step_title" in slide.slot_values:
        return _join_title_parts(
            slide.slot_values["step_no"],
            slide.slot_values["step_title"],
        )
    title_alias = _pattern_title_alias(pattern)
    if title_alias is not None and title_alias in slide.slot_values:
        return slide.slot_values[title_alias]
    return slide.goal


def _join_title_parts(prefix: str, label: str) -> str:
    normalized_prefix = prefix.strip()
    normalized_label = label.strip()
    if not normalized_prefix:
        return normalized_label
    if not normalized_label:
        return normalized_prefix
    if normalized_prefix[-1].isalnum():
        return f"{normalized_prefix} {normalized_label}"
    return f"{normalized_prefix} {normalized_label}"


def _section_title_alias(section) -> str | None:
    for slot in section.slots:
        if slot.slot_type == "title":
            return slot.alias
    return None


def _ordered_text_slots(section) -> list[Any]:
    return sorted(
        (slot for slot in section.slots if slot.slot_type == "text"),
        key=lambda slot: (slot.order or 0, slot.alias or slot.slot_id),
    )


def _pattern_title_alias(pattern: TemplatePatternContract | None) -> str | None:
    if pattern is None:
        return None
    for slot in pattern.slots:
        if slot.slot_type == "title":
            return slot.alias
    return None


def _pattern_body_aliases(pattern: TemplatePatternContract | None) -> tuple[str, ...]:
    if pattern is None:
        return ()
    return tuple(
        slot.alias
        for slot in pattern.slots
        if slot.slot_type == "text" and slot.slot_id.startswith(f"{pattern.kind}.body_")
    )


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
