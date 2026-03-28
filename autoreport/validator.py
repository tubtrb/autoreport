"""Validation helpers for contract-first Autoreport payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from autoreport.models import (
    ContentsSettings,
    ImageSpec,
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


def validate_payload(
    data: dict[str, Any],
    contract: TemplateContract,
    *,
    available_image_refs: Iterable[str] = (),
) -> ReportPayload:
    """Validate one report payload against an active template contract."""

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
        slots: tuple[TemplateSlotContract, ...] = ()
        if require_kind:
            return TemplatePatternContract(
                pattern_id="",
                kind="",
                layout_name="",
                slots=slots,
            )
        return TemplateSectionContract(
            pattern_id="",
            layout_name="",
            slots=slots,
        )

    if not isinstance(raw, dict):
        errors.append(f"Field '{field_name}' must be an object.")
        slots = ()
        if require_kind:
            return TemplatePatternContract(
                pattern_id="",
                kind="",
                layout_name="",
                slots=slots,
            )
        return TemplateSectionContract(
            pattern_id="",
            layout_name="",
            slots=slots,
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

    for key in raw:
        allowed_keys = {"pattern_id", "layout_name", "slots"}
        if require_kind:
            allowed_keys.add("kind")
        if key not in allowed_keys:
            errors.append(f"Field '{field_name}.{key}' is not allowed.")

    if require_kind:
        return TemplatePatternContract(
            pattern_id=pattern_id,
            kind=kind,
            layout_name=layout_name,
            slots=slots,
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
            errors.append(
                f"Field 'slide_patterns[{index}]' must be an object."
            )
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
            errors.append(
                f"Field '{field_name}[{index}]' must be an object."
            )
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


def _validate_payload_slides(
    root: dict[str, Any],
    *,
    contract: TemplateContract,
    available_image_refs: set[str],
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

        pattern = _resolve_pattern_for_slide(
            kind=kind,
            pattern_id=pattern_id,
            prefix=prefix,
            contract=contract,
            errors=errors,
        )
        pattern_slots = {slot.slot_id: slot for slot in pattern.slots} if pattern else {}

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
        elif kind == "metrics":
            items = _validate_metric_items(item, prefix, errors)
        elif kind == "text_image":
            body = _validate_string_list_field(
                item,
                f"{prefix}.body",
                errors,
                min_items=1,
            )
            image = _validate_image_spec(
                item.get("image"),
                field_name=f"{prefix}.image",
                errors=errors,
                available_image_refs=available_image_refs,
            )
            caption = _validate_optional_string(
                item,
                f"{prefix}.caption",
                errors,
            )
            if caption is not None and not caption.strip():
                errors.append(f"Field '{prefix}.caption' must be a non-empty string.")
                caption = None

        slot_overrides = _validate_slot_overrides(
            item,
            prefix=prefix,
            pattern_slots=pattern_slots,
            available_image_refs=available_image_refs,
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


def _resolve_pattern_for_slide(
    *,
    kind: str,
    pattern_id: str | None,
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

    if pattern_id is None:
        return candidates[0]

    for candidate in candidates:
        if candidate.pattern_id == pattern_id:
            return candidate

    errors.append(
        f"Field '{prefix}.pattern_id' is not valid for kind '{kind}'."
    )
    return None


def _validate_metric_items(
    item: dict[str, Any],
    prefix: str,
    errors: list[str],
) -> list[MetricItem]:
    raw = item.get("items")
    if raw is None:
        errors.append(f"Field '{prefix}.items' is required.")
        return []
    if not isinstance(raw, list):
        errors.append(f"Field '{prefix}.items' must be a list.")
        return []
    if not raw:
        errors.append(f"Field '{prefix}.items' must contain at least 1 item.")
        return []

    items: list[MetricItem] = []
    for index, metric_raw in enumerate(raw):
        metric_prefix = f"{prefix}.items[{index}]"
        if not isinstance(metric_raw, dict):
            errors.append(f"Field '{metric_prefix}' must be an object.")
            continue
        label = _validate_required_string(
            metric_raw,
            f"{metric_prefix}.label",
            errors,
        )
        value = metric_raw.get("value")
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"Field '{metric_prefix}.value' must be an integer.")
            value = 0
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


def _validate_image_spec(
    raw: Any,
    *,
    field_name: str,
    errors: list[str],
    available_image_refs: set[str],
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
    if ref_value and ref_value not in available_image_refs:
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


def _field_exists(data: dict[str, Any], field_name: str) -> bool:
    keys = field_name.split(".")
    current: Any = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            return False
        if key not in current:
            return keys[-1] in current
        current = current.get(key)
    return isinstance(current, dict) and keys[-1] in current


def _validate_optional_string(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> str | None:
    keys = field_name.split(".")
    current: Any = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            return None
        if key not in current:
            if keys[-1] in current:
                break
            return None
        current = current.get(key)
    if not isinstance(current, dict):
        return None
    last_key = keys[-1]
    if last_key not in current:
        return None

    value = current[last_key]
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
    keys = field_name.split(".")
    current: Any = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            errors.append(f"Field '{field_name}' is required.")
            return False
        if key not in current:
            if keys[-1] in current:
                break
            errors.append(f"Field '{field_name}' is required.")
            return False
        current = current.get(key)
    if not isinstance(current, dict) or keys[-1] not in current:
        errors.append(f"Field '{field_name}' is required.")
        return False
    value = current[keys[-1]]
    if not isinstance(value, bool):
        errors.append(f"Field '{field_name}' must be a boolean.")
        return False
    return value


def _validate_optional_int(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> int | None:
    keys = field_name.split(".")
    current: Any = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            return None
        if key not in current:
            if keys[-1] in current:
                break
            return None
        current = current.get(key)
    if not isinstance(current, dict) or keys[-1] not in current:
        return None
    value = current[keys[-1]]
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
    keys = field_name.split(".")
    current: Any = data
    for key in keys[:-1]:
        if not isinstance(current, dict):
            errors.append(
                f"Field '{field_name}' must be a list of non-empty strings."
            )
            return []
        if key not in current:
            if keys[-1] in current:
                break
            errors.append(
                f"Field '{field_name}' must be a list of non-empty strings."
            )
            return []
        current = current.get(key)

    if not isinstance(current, dict):
        errors.append(
            f"Field '{field_name}' must be a list of non-empty strings."
        )
        return []

    last_key = keys[-1]
    if last_key not in current:
        errors.append(f"Field '{field_name}' is required.")
        return []

    value = current[last_key]
    if not isinstance(value, list):
        errors.append(
            f"Field '{field_name}' must be a list of non-empty strings."
        )
        return []
    if len(value) < min_items:
        errors.append(
            f"Field '{field_name}' must contain at least {min_items} item"
            + ("s." if min_items > 1 else ".")
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
        normalized_items: list[str] = []
        if not value:
            errors.append(f"Field '{field_name}' must contain at least 1 item.")
            return None
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
