"""Validation helpers for contract-first Autoreport payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

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
    TemplateSectionContract,
    TemplateSlotContract,
    TEMPLATE_CONTRACT_VERSION,
    TitleSlidePayload,
)


ALLOWED_TEMPLATE_SLOT_TYPES = {"title", "text", "image", "caption"}
ALLOWED_ORIENTATIONS = {"horizontal", "vertical", "stack"}
ALLOWED_IMAGE_LAYOUTS = {"auto", *ALLOWED_ORIENTATIONS}
ALLOWED_SLIDE_KINDS = {"text", "metrics", "text_image"}
ALLOWED_IMAGE_FITS = {"contain", "cover"}


class ValidationError(Exception):
    """Raised when content fails contract or payload validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_template_contract(data: dict[str, Any]) -> TemplateContract:
    """Validate a template contract mapping and return a typed model."""

    root = _unwrap_root_mapping(
        data,
        wrapper_key="template_contract",
        empty_message="Template contract content must be a YAML mapping.",
    )
    errors: list[str] = []

    contract_version = _validate_required_string(
        root,
        "contract_version",
        errors,
    )
    template_id = _validate_required_string(root, "template_id", errors)
    template_label = _validate_required_string(root, "template_label", errors)
    template_source = _validate_required_string(root, "template_source", errors)

    title_slide = _validate_section_contract(
        root,
        field_name="title_slide",
        errors=errors,
        require_kind=False,
    )
    contents_slide = _validate_section_contract(
        root,
        field_name="contents_slide",
        errors=errors,
        require_kind=False,
    )
    slide_patterns = _validate_slide_patterns(root, errors)

    for key in root:
        if key not in {
            "contract_version",
            "template_id",
            "template_label",
            "template_source",
            "title_slide",
            "contents_slide",
            "slide_patterns",
        }:
            errors.append(f"Field '{key}' is not allowed.")

    if contract_version and contract_version != TEMPLATE_CONTRACT_VERSION:
        errors.append(
            "Field 'contract_version' must equal "
            f"'{TEMPLATE_CONTRACT_VERSION}'."
        )

    if errors:
        raise ValidationError(errors)

    return TemplateContract(
        contract_version=contract_version,
        template_id=template_id,
        template_label=template_label,
        template_source=template_source,
        title_slide=title_slide,
        contents_slide=contents_slide,
        slide_patterns=tuple(slide_patterns),
    )


def validate_authoring_payload(
    data: dict[str, Any],
    contract: TemplateContract,
    *,
    available_image_refs: Iterable[str] = (),
    enforce_image_refs: bool = True,
) -> AuthoringPayload:
    """Validate one authoring payload against an active template contract."""

    root = _unwrap_root_mapping(
        data,
        wrapper_key="authoring_payload",
        empty_message="Authoring payload content must be a YAML mapping.",
    )
    errors: list[str] = []
    available_refs = set(available_image_refs)

    payload_version = _validate_required_string(root, "payload_version", errors)
    template_id = _validate_required_string(root, "template_id", errors)
    if payload_version and payload_version != AUTHORING_PAYLOAD_VERSION:
        errors.append(
            "Field 'payload_version' must equal "
            f"'{AUTHORING_PAYLOAD_VERSION}'."
        )
    if template_id and template_id != contract.template_id:
        errors.append(
            f"Field 'template_id' must match '{contract.template_id}'."
        )

    deck_context = _validate_deck_context(root, errors)
    title_slide = _validate_title_slide(root, errors)
    contents = _validate_contents(root, errors)
    slides = _validate_authoring_slides(
        root,
        contract=contract,
        available_image_refs=available_refs,
        enforce_image_refs=enforce_image_refs,
        errors=errors,
    )

    for key in root:
        if key not in {
            "payload_version",
            "template_id",
            "deck_context",
            "title_slide",
            "contents",
            "slides",
        }:
            errors.append(f"Field '{key}' is not allowed.")

    if errors:
        raise ValidationError(errors)

    return AuthoringPayload(
        payload_version=payload_version,
        template_id=template_id,
        deck_context=deck_context,
        title_slide=title_slide,
        contents=contents,
        slides=slides,
    )


def validate_payload(
    data: dict[str, Any],
    contract: TemplateContract,
    *,
    available_image_refs: Iterable[str] = (),
    enforce_image_refs: bool = True,
) -> ReportPayload:
    """Validate one runtime report payload against an active template contract."""

    root = _unwrap_root_mapping(
        data,
        wrapper_key="report_payload",
        empty_message="Report payload content must be a YAML mapping.",
    )
    errors: list[str] = []
    available_refs = set(available_image_refs)

    payload_version = _validate_required_string(root, "payload_version", errors)
    template_id = _validate_required_string(root, "template_id", errors)
    if payload_version and payload_version != REPORT_PAYLOAD_VERSION:
        errors.append(
            "Field 'payload_version' must equal "
            f"'{REPORT_PAYLOAD_VERSION}'."
        )
    if template_id and template_id != contract.template_id:
        errors.append(
            f"Field 'template_id' must match '{contract.template_id}'."
        )

    title_slide = _validate_title_slide(root, errors)
    contents = _validate_contents(root, errors)
    slides = _validate_payload_slides(
        root,
        contract=contract,
        available_image_refs=available_refs,
        enforce_image_refs=enforce_image_refs,
        errors=errors,
    )

    for key in root:
        if key not in {
            "payload_version",
            "template_id",
            "title_slide",
            "contents",
            "slides",
        }:
            errors.append(f"Field '{key}' is not allowed.")

    if errors:
        raise ValidationError(errors)

    return ReportPayload(
        payload_version=payload_version,
        template_id=template_id,
        title_slide=title_slide,
        contents=contents,
        slides=slides,
    )


def _unwrap_root_mapping(
    data: Any,
    *,
    wrapper_key: str,
    empty_message: str,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValidationError([empty_message])

    if wrapper_key not in data:
        return data

    if len(data) != 1:
        raise ValidationError(
            [f"Field '{wrapper_key}' must be the only top-level key."]
        )

    wrapped = data[wrapper_key]
    if not isinstance(wrapped, dict):
        raise ValidationError([empty_message])
    return wrapped


def _validate_section_contract(
    root: dict[str, Any],
    *,
    field_name: str,
    errors: list[str],
    require_kind: bool,
) -> TemplateSectionContract | TemplatePatternContract:
    raw = root.get(field_name)
    if raw is None:
        errors.append(f"Field '{field_name}' is required.")
        if require_kind:
            return TemplatePatternContract(
                pattern_id="",
                kind="",
                layout_name="",
                slots=(),
            )
        return TemplateSectionContract(
            pattern_id="",
            layout_name="",
            slots=(),
        )

    if not isinstance(raw, dict):
        errors.append(f"Field '{field_name}' must be an object.")
        if require_kind:
            return TemplatePatternContract(
                pattern_id="",
                kind="",
                layout_name="",
                slots=(),
            )
        return TemplateSectionContract(
            pattern_id="",
            layout_name="",
            slots=(),
        )

    pattern_id = _validate_required_string(raw, f"{field_name}.pattern_id", errors)
    layout_name = _validate_required_string(raw, f"{field_name}.layout_name", errors)
    kind = ""
    if require_kind:
        kind = _validate_required_string(raw, f"{field_name}.kind", errors)
        if kind and kind not in ALLOWED_SLIDE_KINDS:
            errors.append(
                f"Field '{field_name}.kind' must be one of "
                "'text', 'metrics', or 'text_image'."
            )

    slots = _validate_slot_contract_list(
        raw,
        field_name=f"{field_name}.slots",
        errors=errors,
    )

    image_count = _validate_optional_int(raw, f"{field_name}.image_count", errors)
    image_layout = _validate_optional_string(
        raw,
        f"{field_name}.image_layout",
        errors,
    )
    caption_slots = _validate_optional_int(
        raw,
        f"{field_name}.caption_slots",
        errors,
    )
    body_slot_count = _validate_optional_int(
        raw,
        f"{field_name}.body_slot_count",
        errors,
    )

    if image_count is not None and image_count < 0:
        errors.append(f"Field '{field_name}.image_count' must be at least 0.")
    if image_layout is not None and image_layout not in ALLOWED_ORIENTATIONS:
        errors.append(
            f"Field '{field_name}.image_layout' must be one of "
            "'horizontal', 'vertical', or 'stack'."
        )
    if caption_slots is not None and caption_slots < 0:
        errors.append(f"Field '{field_name}.caption_slots' must be at least 0.")
    if body_slot_count is not None and body_slot_count < 0:
        errors.append(f"Field '{field_name}.body_slot_count' must be at least 0.")

    allowed_keys = {"pattern_id", "layout_name", "slots"}
    if require_kind:
        allowed_keys |= {
            "kind",
            "image_count",
            "image_layout",
            "caption_slots",
            "body_slot_count",
        }
    for key in raw:
        if key not in allowed_keys:
            errors.append(f"Field '{field_name}.{key}' is not allowed.")

    if require_kind:
        return TemplatePatternContract(
            pattern_id=pattern_id,
            kind=kind,
            layout_name=layout_name,
            slots=slots,
            image_count=image_count,
            image_layout=image_layout,
            caption_slots=caption_slots,
            body_slot_count=body_slot_count,
        )
    return TemplateSectionContract(
        pattern_id=pattern_id,
        layout_name=layout_name,
        slots=slots,
    )


def _validate_slide_patterns(
    root: dict[str, Any],
    errors: list[str],
) -> list[TemplatePatternContract]:
    raw = root.get("slide_patterns")
    if raw is None:
        errors.append("Field 'slide_patterns' is required.")
        return []
    if not isinstance(raw, list):
        errors.append("Field 'slide_patterns' must be a list.")
        return []
    if not raw:
        errors.append("Field 'slide_patterns' must contain at least 1 item.")
        return []

    patterns: list[TemplatePatternContract] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"Field 'slide_patterns[{index}]' must be an object.")
            continue
        pattern = _validate_section_contract(
            {"slide_patterns": item},
            field_name="slide_patterns",
            errors=errors,
            require_kind=True,
        )
        if pattern.pattern_id:
            if pattern.pattern_id in seen_ids:
                errors.append(
                    f"Field 'slide_patterns[{index}].pattern_id' must be unique."
                )
            seen_ids.add(pattern.pattern_id)
        patterns.append(pattern)

    return patterns


def _validate_slot_contract_list(
    raw: dict[str, Any],
    *,
    field_name: str,
    errors: list[str],
) -> tuple[TemplateSlotContract, ...]:
    slots_raw = raw.get("slots")
    if slots_raw is None:
        errors.append(f"Field '{field_name}' is required.")
        return ()
    if not isinstance(slots_raw, list):
        errors.append(f"Field '{field_name}' must be a list.")
        return ()
    if not slots_raw:
        errors.append(f"Field '{field_name}' must contain at least 1 item.")
        return ()

    slots: list[TemplateSlotContract] = []
    seen_ids: set[str] = set()
    for index, slot_raw in enumerate(slots_raw):
        if not isinstance(slot_raw, dict):
            errors.append(f"Field '{field_name}[{index}]' must be an object.")
            continue
        slot_prefix = f"{field_name}[{index}]"
        slot_id = _validate_required_string(slot_raw, f"{slot_prefix}.slot_id", errors)
        alias = _validate_required_string(slot_raw, f"{slot_prefix}.alias", errors)
        slot_type = _validate_required_string(
            slot_raw,
            f"{slot_prefix}.slot_type",
            errors,
        )
        required = _validate_required_bool(
            slot_raw,
            f"{slot_prefix}.required",
            errors,
        )
        orientation = _validate_optional_string(
            slot_raw,
            f"{slot_prefix}.orientation",
            errors,
        )
        order = _validate_optional_int(
            slot_raw,
            f"{slot_prefix}.order",
            errors,
        )

        if slot_id:
            if slot_id in seen_ids:
                errors.append(f"Field '{slot_prefix}.slot_id' must be unique.")
            seen_ids.add(slot_id)
        if slot_type and slot_type not in ALLOWED_TEMPLATE_SLOT_TYPES:
            errors.append(
                f"Field '{slot_prefix}.slot_type' must be one of "
                "'title', 'text', 'image', or 'caption'."
            )
        if orientation and orientation not in ALLOWED_ORIENTATIONS:
            errors.append(
                f"Field '{slot_prefix}.orientation' must be one of "
                "'horizontal', 'vertical', or 'stack'."
            )
        if order is not None and order < 1:
            errors.append(f"Field '{slot_prefix}.order' must be at least 1.")

        for key in slot_raw:
            if key not in {
                "slot_id",
                "alias",
                "slot_type",
                "required",
                "orientation",
                "order",
            }:
                errors.append(f"Field '{slot_prefix}.{key}' is not allowed.")

        slots.append(
            TemplateSlotContract(
                slot_id=slot_id,
                alias=alias,
                slot_type=slot_type,
                required=required,
                orientation=orientation,
                order=order,
            )
        )

    return tuple(slots)


def _validate_deck_context(
    root: dict[str, Any],
    errors: list[str],
) -> DeckContext:
    raw = root.get("deck_context", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        errors.append("Field 'deck_context' must be an object.")
        return DeckContext()

    audience = _validate_optional_string(raw, "deck_context.audience", errors)
    tone = _validate_optional_string(raw, "deck_context.tone", errors)
    objective = _validate_optional_string(raw, "deck_context.objective", errors)

    for key in raw:
        if key not in {"audience", "tone", "objective"}:
            errors.append(f"Field 'deck_context.{key}' is not allowed.")

    return DeckContext(
        audience=audience,
        tone=tone,
        objective=objective,
    )


def _validate_title_slide(
    root: dict[str, Any],
    errors: list[str],
) -> TitleSlidePayload:
    raw = root.get("title_slide")
    if raw is None:
        errors.append("Field 'title_slide' is required.")
        return TitleSlidePayload(title="", subtitle=[])
    if not isinstance(raw, dict):
        errors.append("Field 'title_slide' must be an object.")
        return TitleSlidePayload(title="", subtitle=[])

    title = _validate_required_string(raw, "title_slide.title", errors)
    subtitle = _validate_string_list_field(
        raw,
        "title_slide.subtitle",
        errors,
        min_items=1,
    )

    for key in raw:
        if key not in {"title", "subtitle"}:
            errors.append(f"Field 'title_slide.{key}' is not allowed.")

    return TitleSlidePayload(title=title, subtitle=subtitle)


def _validate_contents(
    root: dict[str, Any],
    errors: list[str],
) -> ContentsSettings:
    raw = root.get("contents")
    if raw is None:
        return ContentsSettings(enabled=True)
    if not isinstance(raw, dict):
        errors.append("Field 'contents' must be an object.")
        return ContentsSettings(enabled=True)

    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        errors.append("Field 'contents.enabled' must be a boolean.")
        enabled = True

    for key in raw:
        if key != "enabled":
            errors.append(f"Field 'contents.{key}' is not allowed.")

    return ContentsSettings(enabled=enabled)


def _validate_authoring_slides(
    root: dict[str, Any],
    *,
    contract: TemplateContract,
    available_image_refs: set[str],
    enforce_image_refs: bool,
    errors: list[str],
) -> list[AuthoringSlide]:
    raw = root.get("slides")
    if raw is None:
        errors.append("Field 'slides' is required.")
        return []
    if not isinstance(raw, list):
        errors.append("Field 'slides' must be a list.")
        return []
    if not raw:
        errors.append("Field 'slides' must contain at least 1 item.")
        return []

    slides: list[AuthoringSlide] = []
    seen_slide_nos: set[int] = set()
    for index, item in enumerate(raw):
        prefix = f"slides[{index}]"
        if not isinstance(item, dict):
            errors.append(f"Field '{prefix}' must be an object.")
            continue

        slide_no = _validate_required_int(item, f"{prefix}.slide_no", errors)
        if slide_no is not None:
            if slide_no < 1:
                errors.append(f"Field '{prefix}.slide_no' must be at least 1.")
            elif slide_no in seen_slide_nos:
                errors.append(f"Field '{prefix}.slide_no' must be unique.")
            else:
                seen_slide_nos.add(slide_no)
            if slide_no != index + 1:
                errors.append(
                    f"Field '{prefix}.slide_no' must equal {index + 1}."
                )

        goal = _validate_required_string(item, f"{prefix}.goal", errors)
        include_in_contents = item.get("include_in_contents", True)
        if not isinstance(include_in_contents, bool):
            errors.append(
                f"Field '{prefix}.include_in_contents' must be a boolean."
            )
            include_in_contents = True

        context = _validate_authoring_context(item, prefix=prefix, errors=errors)
        assets = _validate_authoring_assets(
            item,
            prefix=prefix,
            errors=errors,
            available_image_refs=available_image_refs,
            enforce_image_refs=enforce_image_refs,
        )
        layout_request = _validate_layout_request(item, prefix=prefix, errors=errors)

        if layout_request is not None:
            _validate_authoring_slide_shape(
                prefix=prefix,
                context=context,
                assets=assets,
                layout_request=layout_request,
                errors=errors,
            )
            _resolve_pattern_for_authoring_slide(
                layout_request=layout_request,
                image_count=(
                    layout_request.image_count
                    if layout_request.image_count is not None
                    else len(assets.images)
                ),
                prefix=prefix,
                contract=contract,
                errors=errors,
            )

        for key in item:
            if key not in {
                "slide_no",
                "goal",
                "include_in_contents",
                "context",
                "assets",
                "layout_request",
            }:
                errors.append(f"Field '{prefix}.{key}' is not allowed.")

        slides.append(
            AuthoringSlide(
                slide_no=(0 if slide_no is None else slide_no),
                goal=goal,
                include_in_contents=include_in_contents,
                context=context,
                assets=assets,
                layout_request=layout_request,
            )
        )

    return slides


def _validate_authoring_context(
    item: dict[str, Any],
    *,
    prefix: str,
    errors: list[str],
) -> AuthoringSlideContext:
    raw = item.get("context")
    if raw is None:
        errors.append(f"Field '{prefix}.context' is required.")
        return AuthoringSlideContext()
    if not isinstance(raw, dict):
        errors.append(f"Field '{prefix}.context' must be an object.")
        return AuthoringSlideContext()

    summary = _validate_optional_string(raw, f"{prefix}.context.summary", errors)
    bullets = _validate_optional_string_list_field(
        raw,
        f"{prefix}.context.bullets",
        errors,
    )
    metrics = _validate_optional_metric_items(
        raw,
        field_name=f"{prefix}.context.metrics",
        errors=errors,
    )
    caption = _validate_optional_string(raw, f"{prefix}.context.caption", errors)

    for key in raw:
        if key not in {"summary", "bullets", "metrics", "caption"}:
            errors.append(f"Field '{prefix}.context.{key}' is not allowed.")

    return AuthoringSlideContext(
        summary=summary,
        bullets=bullets,
        metrics=metrics,
        caption=caption,
    )


def _validate_authoring_assets(
    item: dict[str, Any],
    *,
    prefix: str,
    errors: list[str],
    available_image_refs: set[str],
    enforce_image_refs: bool,
) -> AuthoringSlideAssets:
    raw = item.get("assets", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        errors.append(f"Field '{prefix}.assets' must be an object.")
        return AuthoringSlideAssets()

    images: list[ImageSpec] = []
    if "images" in raw:
        images = _validate_image_spec_list(
            raw.get("images"),
            field_name=f"{prefix}.assets.images",
            errors=errors,
            available_image_refs=available_image_refs,
            enforce_image_refs=enforce_image_refs,
        )

    for key in raw:
        if key != "images":
            errors.append(f"Field '{prefix}.assets.{key}' is not allowed.")

    return AuthoringSlideAssets(images=images)


def _validate_layout_request(
    item: dict[str, Any],
    *,
    prefix: str,
    errors: list[str],
) -> LayoutRequest | None:
    raw = item.get("layout_request")
    if raw is None:
        errors.append(f"Field '{prefix}.layout_request' is required.")
        return None
    if not isinstance(raw, dict):
        errors.append(f"Field '{prefix}.layout_request' must be an object.")
        return None

    kind = _validate_required_string(raw, f"{prefix}.layout_request.kind", errors)
    pattern_id = _validate_optional_string(
        raw,
        f"{prefix}.layout_request.pattern_id",
        errors,
    )
    image_count = _validate_optional_int(
        raw,
        f"{prefix}.layout_request.image_count",
        errors,
    )
    image_orientation = (
        _validate_optional_string(
            raw,
            f"{prefix}.layout_request.image_orientation",
            errors,
        )
        or "auto"
    )

    if kind and kind not in ALLOWED_SLIDE_KINDS:
        errors.append(
            f"Field '{prefix}.layout_request.kind' must be one of "
            "'text', 'metrics', or 'text_image'."
        )
    if image_count is not None and image_count < 0:
        errors.append(f"Field '{prefix}.layout_request.image_count' must be at least 0.")
    if image_orientation not in ALLOWED_IMAGE_LAYOUTS:
        errors.append(
            f"Field '{prefix}.layout_request.image_orientation' must be one of "
            "'auto', 'horizontal', 'vertical', or 'stack'."
        )

    for key in raw:
        if key not in {
            "kind",
            "pattern_id",
            "image_count",
            "image_orientation",
        }:
            errors.append(f"Field '{prefix}.layout_request.{key}' is not allowed.")

    return LayoutRequest(
        kind=kind,
        pattern_id=pattern_id,
        image_count=image_count,
        image_orientation=image_orientation,
    )


def _validate_authoring_slide_shape(
    *,
    prefix: str,
    context: AuthoringSlideContext,
    assets: AuthoringSlideAssets,
    layout_request: LayoutRequest,
    errors: list[str],
) -> None:
    has_text = bool(context.summary or context.bullets)
    actual_image_count = len(assets.images)

    if layout_request.kind == "text":
        if not has_text:
            errors.append(
                f"Field '{prefix}.context' must provide 'summary' or 'bullets' for kind 'text'."
            )
        if context.metrics:
            errors.append(
                f"Field '{prefix}.context.metrics' is not allowed for kind 'text'."
            )
        if context.caption is not None:
            errors.append(
                f"Field '{prefix}.context.caption' is not allowed for kind 'text'."
            )
        if assets.images:
            errors.append(
                f"Field '{prefix}.assets.images' is not allowed for kind 'text'."
            )
        if layout_request.image_count not in {None, 0}:
            errors.append(
                f"Field '{prefix}.layout_request.image_count' is not allowed for kind 'text'."
            )
        if layout_request.image_orientation != "auto":
            errors.append(
                f"Field '{prefix}.layout_request.image_orientation' is not allowed for kind 'text'."
            )
        return

    if layout_request.kind == "metrics":
        if not context.metrics:
            errors.append(
                f"Field '{prefix}.context.metrics' must contain at least 1 item for kind 'metrics'."
            )
        if context.summary is not None:
            errors.append(
                f"Field '{prefix}.context.summary' is not allowed for kind 'metrics'."
            )
        if context.bullets:
            errors.append(
                f"Field '{prefix}.context.bullets' is not allowed for kind 'metrics'."
            )
        if context.caption is not None:
            errors.append(
                f"Field '{prefix}.context.caption' is not allowed for kind 'metrics'."
            )
        if assets.images:
            errors.append(
                f"Field '{prefix}.assets.images' is not allowed for kind 'metrics'."
            )
        if layout_request.image_count not in {None, 0}:
            errors.append(
                f"Field '{prefix}.layout_request.image_count' is not allowed for kind 'metrics'."
            )
        if layout_request.image_orientation != "auto":
            errors.append(
                f"Field '{prefix}.layout_request.image_orientation' is not allowed for kind 'metrics'."
            )
        return

    if not has_text:
        errors.append(
            f"Field '{prefix}.context' must provide 'summary' or 'bullets' for kind 'text_image'."
        )
    if context.metrics:
        errors.append(
            f"Field '{prefix}.context.metrics' is not allowed for kind 'text_image'."
        )
    if actual_image_count < 1:
        errors.append(
            f"Field '{prefix}.assets.images' must contain at least 1 item for kind 'text_image'."
        )
    if (
        layout_request.image_count is not None
        and layout_request.image_count != actual_image_count
    ):
        errors.append(
            f"Field '{prefix}.layout_request.image_count' must match the number of provided images."
        )


def _validate_payload_slides(
    root: dict[str, Any],
    *,
    contract: TemplateContract,
    available_image_refs: set[str],
    enforce_image_refs: bool,
    errors: list[str],
) -> list[PayloadSlide]:
    raw = root.get("slides")
    if raw is None:
        errors.append("Field 'slides' is required.")
        return []
    if not isinstance(raw, list):
        errors.append("Field 'slides' must be a list.")
        return []
    if not raw:
        errors.append("Field 'slides' must contain at least 1 item.")
        return []

    slides: list[PayloadSlide] = []
    for index, item in enumerate(raw):
        prefix = f"slides[{index}]"
        if not isinstance(item, dict):
            errors.append(f"Field '{prefix}' must be an object.")
            continue

        kind = _validate_required_string(item, f"{prefix}.kind", errors)
        title = _validate_required_string(item, f"{prefix}.title", errors)
        include_in_contents = item.get("include_in_contents", True)
        if not isinstance(include_in_contents, bool):
            errors.append(
                f"Field '{prefix}.include_in_contents' must be a boolean."
            )
            include_in_contents = True

        pattern_id = _validate_optional_string(
            item,
            f"{prefix}.pattern_id",
            errors,
        )
        if kind and kind not in ALLOWED_SLIDE_KINDS:
            errors.append(
                f"Field '{prefix}.kind' must be one of "
                "'text', 'metrics', or 'text_image'."
            )

        pattern = _resolve_pattern_for_runtime_slide(
            kind=kind,
            pattern_id=pattern_id,
            item=item,
            prefix=prefix,
            contract=contract,
            errors=errors,
        )
        pattern_slots = {slot.slot_id: slot for slot in pattern.slots} if pattern else {}
        slot_overrides = _validate_slot_overrides(
            item,
            prefix=prefix,
            pattern_slots=pattern_slots,
            available_image_refs=available_image_refs,
            enforce_image_refs=enforce_image_refs,
            errors=errors,
        )

        body: list[str] = []
        items: list[MetricItem] = []
        image: ImageSpec | None = None
        caption: str | None = None

        if kind == "text":
            body = _validate_string_list_field(
                item,
                f"{prefix}.body",
                errors,
                min_items=1,
            )
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="items",
                errors=errors,
            )
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="image",
                errors=errors,
            )
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="caption",
                errors=errors,
            )
        elif kind == "metrics":
            items = _validate_metric_items(item, prefix, errors)
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="body",
                errors=errors,
            )
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="image",
                errors=errors,
            )
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="caption",
                errors=errors,
            )
        elif kind == "text_image":
            body = _validate_string_list_field(
                item,
                f"{prefix}.body",
                errors,
                min_items=1,
            )
            if "image" in item:
                image = _validate_image_spec(
                    item.get("image"),
                    field_name=f"{prefix}.image",
                    errors=errors,
                    available_image_refs=available_image_refs,
                    enforce_image_refs=enforce_image_refs,
                )
            caption = _validate_optional_string(
                item,
                f"{prefix}.caption",
                errors,
            )
            if image is None and not _has_image_slot_override(slot_overrides):
                errors.append(f"Field '{prefix}.image' is required.")
            _validate_disallowed_slide_field(
                item,
                prefix=prefix,
                kind=kind,
                field_name="items",
                errors=errors,
            )

        for key in item:
            if key not in {
                "kind",
                "title",
                "include_in_contents",
                "pattern_id",
                "body",
                "items",
                "image",
                "caption",
                "slot_overrides",
            }:
                errors.append(f"Field '{prefix}.{key}' is not allowed.")

        slides.append(
            PayloadSlide(
                kind=kind,
                title=title,
                include_in_contents=include_in_contents,
                pattern_id=pattern.pattern_id if pattern is not None else pattern_id,
                body=body,
                items=items,
                image=image,
                caption=caption,
                slot_overrides=slot_overrides,
            )
        )

    return slides


def _resolve_pattern_for_authoring_slide(
    *,
    layout_request: LayoutRequest,
    image_count: int,
    prefix: str,
    contract: TemplateContract,
    errors: list[str],
) -> TemplatePatternContract | None:
    requested_image_count = image_count if layout_request.kind == "text_image" else 0
    return _match_template_pattern(
        contract=contract,
        kind=layout_request.kind,
        pattern_id=layout_request.pattern_id,
        image_count=requested_image_count,
        image_orientation=layout_request.image_orientation,
        prefix=prefix,
        field_prefix=f"{prefix}.layout_request",
        errors=errors,
    )


def _resolve_pattern_for_runtime_slide(
    *,
    kind: str,
    pattern_id: str | None,
    item: dict[str, Any],
    prefix: str,
    contract: TemplateContract,
    errors: list[str],
) -> TemplatePatternContract | None:
    if not kind or kind not in ALLOWED_SLIDE_KINDS:
        return None

    candidates = [
        pattern
        for pattern in contract.slide_patterns
        if pattern.kind == kind
    ]
    if not candidates:
        errors.append(
            f"Field '{prefix}.kind' is not supported by template '{contract.template_id}'."
        )
        return None

    if pattern_id is not None:
        return _match_template_pattern(
            contract=contract,
            kind=kind,
            pattern_id=pattern_id,
            image_count=None,
            image_orientation="auto",
            prefix=prefix,
            field_prefix=prefix,
            errors=errors,
        )

    if kind != "text_image":
        if len(candidates) > 1:
            errors.append(
                f"Field '{prefix}.pattern_id' is required because template "
                f"'{contract.template_id}' defines multiple patterns for kind '{kind}'."
            )
            return None
        return candidates[0]

    requested_image_count = _infer_runtime_image_count(item)
    matches = [
        candidate
        for candidate in candidates
        if _pattern_image_count(candidate) == requested_image_count
    ]
    if matches:
        return matches[0]

    errors.append(
        f"Field '{prefix}.pattern_id' is required because template "
        f"'{contract.template_id}' does not define a text_image pattern with "
        f"image_count={requested_image_count}."
    )
    return None


def _match_template_pattern(
    *,
    contract: TemplateContract,
    kind: str,
    pattern_id: str | None,
    image_count: int | None,
    image_orientation: str,
    prefix: str,
    field_prefix: str,
    errors: list[str],
) -> TemplatePatternContract | None:
    candidates = [
        pattern
        for pattern in contract.slide_patterns
        if pattern.kind == kind
    ]
    if not candidates:
        errors.append(
            f"Field '{field_prefix}.kind' is not supported by template '{contract.template_id}'."
        )
        return None

    if pattern_id is not None:
        for candidate in candidates:
            if candidate.pattern_id != pattern_id:
                continue
            if (
                image_count is not None
                and _pattern_image_count(candidate) != image_count
            ):
                errors.append(
                    f"Field '{field_prefix}.pattern_id' does not match image_count={image_count}."
                )
                return candidate
            if (
                image_orientation != "auto"
                and _pattern_image_layout(candidate) != image_orientation
            ):
                errors.append(
                    f"Field '{field_prefix}.pattern_id' does not match image_orientation='{image_orientation}'."
                )
                return candidate
            return candidate

        errors.append(
            f"Field '{field_prefix}.pattern_id' is not valid for kind '{kind}'."
        )
        return None

    matches: list[TemplatePatternContract] = []
    for candidate in candidates:
        if image_count is not None and _pattern_image_count(candidate) != image_count:
            continue
        if image_orientation != "auto":
            if _pattern_image_layout(candidate) != image_orientation:
                continue
        matches.append(candidate)

    if matches:
        return matches[0]

    requested_shape = [f"kind '{kind}'"]
    if image_count is not None:
        requested_shape.append(f"image_count={image_count}")
    if image_orientation != "auto":
        requested_shape.append(f"image_orientation='{image_orientation}'")
    errors.append(
        f"Field '{prefix}.layout_request' does not match any pattern in template "
        f"'{contract.template_id}' for {', '.join(requested_shape)}."
    )
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
    orientation = image_slots[0].orientation
    return "stack" if orientation is None else orientation


def _validate_disallowed_slide_field(
    item: dict[str, Any],
    *,
    prefix: str,
    kind: str,
    field_name: str,
    errors: list[str],
) -> None:
    if field_name in item:
        errors.append(
            f"Field '{prefix}.{field_name}' is not allowed for kind '{kind}'."
        )


def _validate_metric_items(
    item: dict[str, Any],
    prefix: str,
    errors: list[str],
) -> list[MetricItem]:
    return _validate_required_metric_items(
        item,
        field_name=f"{prefix}.items",
        errors=errors,
    )


def _validate_required_metric_items(
    data: dict[str, Any],
    *,
    field_name: str,
    errors: list[str],
) -> list[MetricItem]:
    if not _field_exists(data, field_name):
        errors.append(f"Field '{field_name}' is required.")
        return []
    items = _validate_optional_metric_items(data, field_name=field_name, errors=errors)
    if not items:
        errors.append(f"Field '{field_name}' must contain at least 1 item.")
    return items


def _validate_optional_metric_items(
    data: dict[str, Any],
    *,
    field_name: str,
    errors: list[str],
) -> list[MetricItem]:
    container, last_key = _resolve_field_container(data, field_name)
    if container is None or last_key not in container:
        return []

    raw = container[last_key]
    if not isinstance(raw, list):
        errors.append(f"Field '{field_name}' must be a list.")
        return []

    items: list[MetricItem] = []
    for index, metric_raw in enumerate(raw):
        metric_prefix = f"{field_name}[{index}]"
        if not isinstance(metric_raw, dict):
            errors.append(f"Field '{metric_prefix}' must be an object.")
            continue
        label = _validate_required_string(
            metric_raw,
            f"{metric_prefix}.label",
            errors,
        )
        value = metric_raw.get("value")
        if isinstance(value, bool):
            errors.append(
                f"Field '{metric_prefix}.value' must be an integer or non-empty string."
            )
            value = ""
        elif isinstance(value, str):
            value = value.strip()
            if not value:
                errors.append(
                    f"Field '{metric_prefix}.value' must be an integer or non-empty string."
                )
                value = ""
        elif not isinstance(value, int):
            errors.append(
                f"Field '{metric_prefix}.value' must be an integer or non-empty string."
            )
            value = ""
        for key in metric_raw:
            if key not in {"label", "value"}:
                errors.append(f"Field '{metric_prefix}.{key}' is not allowed.")
        items.append(MetricItem(label=label, value=value))

    return items


def _validate_slot_overrides(
    item: dict[str, Any],
    *,
    prefix: str,
    pattern_slots: dict[str, TemplateSlotContract],
    available_image_refs: set[str],
    enforce_image_refs: bool,
    errors: list[str],
) -> dict[str, SlotOverride]:
    raw = item.get("slot_overrides", {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        errors.append(f"Field '{prefix}.slot_overrides' must be an object.")
        return {}

    overrides: dict[str, SlotOverride] = {}
    for slot_id, override_raw in raw.items():
        slot_prefix = f"{prefix}.slot_overrides.{slot_id}"
        if slot_id not in pattern_slots:
            errors.append(
                f"Field '{slot_prefix}' targets an unknown slot for the selected pattern."
            )
            continue
        if not isinstance(override_raw, dict):
            errors.append(f"Field '{slot_prefix}' must be an object.")
            continue

        slot_contract = pattern_slots[slot_id]
        text_override: list[str] | None = None
        image_override: ImageSpec | None = None

        if slot_contract.slot_type == "image":
            if set(override_raw) != {"image"}:
                errors.append(
                    f"Field '{slot_prefix}' must only contain 'image' for an image slot."
                )
            image_override = _validate_image_spec(
                override_raw.get("image"),
                field_name=f"{slot_prefix}.image",
                errors=errors,
                available_image_refs=available_image_refs,
                enforce_image_refs=enforce_image_refs,
            )
        else:
            if set(override_raw) != {"text"}:
                errors.append(
                    f"Field '{slot_prefix}' must only contain 'text' for a text slot."
                )
            text_override = _validate_string_or_list(
                override_raw.get("text"),
                field_name=f"{slot_prefix}.text",
                errors=errors,
            )

        overrides[slot_id] = SlotOverride(
            slot_id=slot_id,
            text=text_override,
            image=image_override,
        )

    return overrides


def _has_image_slot_override(slot_overrides: dict[str, SlotOverride]) -> bool:
    return any(
        override.image is not None for override in slot_overrides.values()
    )


def _infer_runtime_image_count(item: dict[str, Any]) -> int:
    count = 0
    if item.get("image") is not None:
        count += 1

    raw_overrides = item.get("slot_overrides")
    if isinstance(raw_overrides, dict):
        for override in raw_overrides.values():
            if isinstance(override, dict) and override.get("image") is not None:
                count += 1

    return 1 if count == 0 else count


def _validate_image_spec_list(
    raw: Any,
    *,
    field_name: str,
    errors: list[str],
    available_image_refs: set[str],
    enforce_image_refs: bool,
) -> list[ImageSpec]:
    if not isinstance(raw, list):
        errors.append(f"Field '{field_name}' must be a list.")
        return []

    images: list[ImageSpec] = []
    for index, item in enumerate(raw):
        image = _validate_image_spec(
            item,
            field_name=f"{field_name}[{index}]",
            errors=errors,
            available_image_refs=available_image_refs,
            enforce_image_refs=enforce_image_refs,
        )
        if image is not None:
            images.append(image)

    return images


def _validate_image_spec(
    raw: Any,
    *,
    field_name: str,
    errors: list[str],
    available_image_refs: set[str],
    enforce_image_refs: bool,
) -> ImageSpec | None:
    if raw is None:
        errors.append(f"Field '{field_name}' is required.")
        return None
    if not isinstance(raw, dict):
        errors.append(f"Field '{field_name}' must be an object.")
        return None

    path_value = _validate_optional_string(raw, f"{field_name}.path", errors)
    ref_value = _validate_optional_string(raw, f"{field_name}.ref", errors)
    fit = _validate_required_string(raw, f"{field_name}.fit", errors)

    if bool(path_value) == bool(ref_value):
        errors.append(
            f"Field '{field_name}' must provide exactly one of 'path' or 'ref'."
        )
    if fit and fit not in ALLOWED_IMAGE_FITS:
        errors.append(
            f"Field '{field_name}.fit' must be either 'contain' or 'cover'."
        )
    if enforce_image_refs and ref_value and ref_value not in available_image_refs:
        errors.append(
            f"Field '{field_name}.ref' does not match a provided image reference."
        )

    for key in raw:
        if key not in {"path", "ref", "fit"}:
            errors.append(f"Field '{field_name}.{key}' is not allowed.")

    return ImageSpec(
        path=(None if path_value is None else Path(path_value)),
        ref=ref_value,
        fit=(fit or "contain"),
    )


def _validate_required_string(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> str:
    if not _field_exists(data, field_name):
        errors.append(f"Field '{field_name}' is required.")
        return ""
    value = _validate_optional_string(data, field_name, errors)
    if value is None:
        return ""
    return value


def _validate_required_int(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> int | None:
    if not _field_exists(data, field_name):
        errors.append(f"Field '{field_name}' is required.")
        return None
    return _validate_optional_int(data, field_name, errors)


def _field_exists(data: dict[str, Any], field_name: str) -> bool:
    container, last_key = _resolve_field_container(data, field_name)
    return container is not None and last_key in container


def _validate_optional_string(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> str | None:
    container, last_key = _resolve_field_container(data, field_name)
    if container is None or last_key not in container:
        return None

    value = container[last_key]
    if not isinstance(value, str):
        errors.append(f"Field '{field_name}' must be a non-empty string.")
        return None

    normalized = value.strip()
    if not normalized:
        errors.append(f"Field '{field_name}' must be a non-empty string.")
        return None
    return normalized


def _validate_required_bool(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> bool:
    if not _field_exists(data, field_name):
        errors.append(f"Field '{field_name}' is required.")
        return False
    container, last_key = _resolve_field_container(data, field_name)
    if container is None or last_key not in container:
        errors.append(f"Field '{field_name}' is required.")
        return False
    value = container[last_key]
    if not isinstance(value, bool):
        errors.append(f"Field '{field_name}' must be a boolean.")
        return False
    return value


def _validate_optional_int(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> int | None:
    container, last_key = _resolve_field_container(data, field_name)
    if container is None or last_key not in container:
        return None
    value = container[last_key]
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"Field '{field_name}' must be an integer.")
        return None
    return value


def _validate_string_list_field(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
    *,
    min_items: int,
) -> list[str]:
    if not _field_exists(data, field_name):
        errors.append(f"Field '{field_name}' is required.")
        return []
    values = _validate_optional_string_list_field(
        data,
        field_name,
        errors,
    )
    if len(values) < min_items:
        errors.append(
            f"Field '{field_name}' must contain at least {min_items} item"
            + ("s." if min_items > 1 else ".")
        )
        return []
    return values


def _validate_optional_string_list_field(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> list[str]:
    container, last_key = _resolve_field_container(data, field_name)
    if container is None or last_key not in container:
        return []

    value = container[last_key]
    if not isinstance(value, list):
        errors.append(
            f"Field '{field_name}' must be a list of non-empty strings."
        )
        return []

    normalized_items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"Field '{field_name}[{index}]' must be a non-empty string."
            )
            continue
        normalized = item.strip()
        if not normalized:
            errors.append(
                f"Field '{field_name}[{index}]' must be a non-empty string."
            )
            continue
        normalized_items.append(normalized)
    return normalized_items


def _validate_string_or_list(
    value: Any,
    *,
    field_name: str,
    errors: list[str],
) -> list[str] | None:
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            errors.append(f"Field '{field_name}' must be a non-empty string.")
            return None
        return [normalized]

    if isinstance(value, list):
        if not value:
            errors.append(f"Field '{field_name}' must contain at least 1 item.")
            return None
        normalized_items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                errors.append(
                    f"Field '{field_name}[{index}]' must be a non-empty string."
                )
                continue
            normalized = item.strip()
            if not normalized:
                errors.append(
                    f"Field '{field_name}[{index}]' must be a non-empty string."
                )
                continue
            normalized_items.append(normalized)
        return normalized_items

    errors.append(
        f"Field '{field_name}' must be a non-empty string or list of non-empty strings."
    )
    return None


def _resolve_field_container(
    data: dict[str, Any],
    field_name: str,
) -> tuple[dict[str, Any] | None, str]:
    keys = field_name.split(".")
    current: Any = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            return None, keys[-1]
        if key not in current:
            if keys[-1] in current:
                return current, keys[-1]
            return None, keys[-1]
        current = current.get(key)
    if not isinstance(current, dict):
        return None, keys[-1]
    return current, keys[-1]
