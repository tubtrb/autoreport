"""Style preset catalog and YAML append helpers for the public web app."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from autoreport.loader import parse_yaml_text
from autoreport.template_flow import detect_payload_kind, serialize_document
from autoreport.templates.manual_procedure_variants import MANUAL_PROCEDURE_VARIANTS
from autoreport.validator import ValidationError


MANUAL_PUBLIC_TEMPLATE_NAME = "autoreport_manual"
DEFAULT_MANUAL_STYLE_PRESET_ID = "manual.procedure.one"

_PUBLIC_VISIBILITY = "public"
_HIDDEN_VISIBILITY = "hidden"
_MANUAL_SECTION_NO_RE = re.compile(r"^(?P<section>\d+)\.?$")
_MANUAL_STEP_NO_RE = re.compile(r"^(?P<section>\d+)\.(?P<step>\d+)$")
_MANUAL_IMAGE_REF_RE = re.compile(r"^image_(?P<index>\d+)$")
_TOKEN_RE = re.compile(r"{{(?P<name>[a-z0-9_]+)}}")

_MANUAL_STYLE_FAMILIES = (
    {
        "family_id": "text",
        "label": "Text",
        "order": 10,
        "visibility": _PUBLIC_VISIBILITY,
    },
    {
        "family_id": "one-image",
        "label": "1 Image",
        "order": 20,
        "visibility": _PUBLIC_VISIBILITY,
    },
    {
        "family_id": "two-images",
        "label": "2 Images",
        "order": 30,
        "visibility": _PUBLIC_VISIBILITY,
    },
    {
        "family_id": "three-images",
        "label": "3 Images",
        "order": 40,
        "visibility": _PUBLIC_VISIBILITY,
    },
    {
        "family_id": "four-images",
        "label": "4 Images",
        "order": 50,
        "visibility": _HIDDEN_VISIBILITY,
    },
    {
        "family_id": "diagram",
        "label": "Diagram",
        "order": 60,
        "visibility": _HIDDEN_VISIBILITY,
    },
    {
        "family_id": "comparison",
        "label": "Comparison",
        "order": 70,
        "visibility": _HIDDEN_VISIBILITY,
    },
)

_MANUAL_STYLE_PRESETS = (
    {
        "preset_id": "manual.section-break",
        "label": "Section Break",
        "family_id": "text",
        "pattern_id": "text.manual.section_break",
        "image_count": 0,
        "description": "Start a new guide section with a text-only divider slide.",
        "tags": ["Text", "Section"],
        "visibility": _PUBLIC_VISIBILITY,
        "order": 10,
        "thumbnail": {
            "background": "#f6fbf8",
            "blocks": [
                {"type": "rect", "role": "accent", "x": 8, "y": 10, "w": 4, "h": 80, "radius": 8},
                {"type": "rect", "role": "text", "x": 18, "y": 20, "w": 46, "h": 10, "radius": 6},
                {"type": "rect", "role": "text", "x": 18, "y": 38, "w": 58, "h": 8, "radius": 5},
                {"type": "rect", "role": "text", "x": 18, "y": 54, "w": 40, "h": 8, "radius": 5},
            ],
        },
        "default_slot_values": {
            "section_no": "{{next_section_index}}.",
            "section_title": "New Section Title",
            "section_subtitle": "Short section setup note.",
        },
    },
    *MANUAL_PROCEDURE_VARIANTS,
    {
        "preset_id": "manual.procedure.two",
        "label": "Style 2",
        "family_id": "two-images",
        "pattern_id": "text_image.manual.procedure.two",
        "image_count": 2,
        "description": "Show two ordered screenshots for a compare-and-contrast step.",
        "tags": ["2 Images", "Procedure"],
        "visibility": _PUBLIC_VISIBILITY,
        "order": 30,
        "thumbnail": {
            "background": "#f7fafc",
            "blocks": [
                {"type": "rect", "role": "accent", "x": 8, "y": 12, "w": 4, "h": 76, "radius": 8},
                {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 40, "h": 9, "radius": 6},
                {"type": "rect", "role": "text", "x": 18, "y": 34, "w": 34, "h": 7, "radius": 5},
                {"type": "rect", "role": "image", "x": 18, "y": 50, "w": 28, "h": 22, "radius": 9},
                {"type": "rect", "role": "image", "x": 52, "y": 50, "w": 28, "h": 22, "radius": 9},
            ],
        },
        "default_slot_values": {
            "step_no": "{{next_step_no}}",
            "step_title": "New Procedure Step",
            "command_or_action": "Action: describe the command or action for this step.",
            "summary": "Short outcome summary for the step.",
            "detail_body": "Explain the detailed procedure here.",
            "image_1": "{{next_image_ref_1}}",
            "caption_1": "{{ordinal_caption_1}}",
            "image_2": "{{next_image_ref_2}}",
            "caption_2": "{{ordinal_caption_2}}",
        },
    },
    {
        "preset_id": "manual.procedure.three",
        "label": "Style 3",
        "family_id": "three-images",
        "pattern_id": "text_image.manual.procedure.three",
        "image_count": 3,
        "description": "Document a longer walkthrough with three ordered screenshots.",
        "tags": ["3 Images", "Procedure"],
        "visibility": _PUBLIC_VISIBILITY,
        "order": 40,
        "thumbnail": {
            "background": "#f7fafc",
            "blocks": [
                {"type": "rect", "role": "accent", "x": 8, "y": 12, "w": 4, "h": 76, "radius": 8},
                {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 42, "h": 9, "radius": 6},
                {"type": "rect", "role": "text", "x": 18, "y": 34, "w": 30, "h": 7, "radius": 5},
                {"type": "rect", "role": "image", "x": 18, "y": 50, "w": 18, "h": 22, "radius": 8},
                {"type": "rect", "role": "image", "x": 42, "y": 50, "w": 18, "h": 22, "radius": 8},
                {"type": "rect", "role": "image", "x": 66, "y": 50, "w": 18, "h": 22, "radius": 8},
            ],
        },
        "default_slot_values": {
            "step_no": "{{next_step_no}}",
            "step_title": "New Procedure Step",
            "command_or_action": "Action: describe the command or action for this step.",
            "summary": "Short outcome summary for the step.",
            "detail_body": "Explain the detailed procedure here.",
            "image_1": "{{next_image_ref_1}}",
            "caption_1": "{{ordinal_caption_1}}",
            "image_2": "{{next_image_ref_2}}",
            "caption_2": "{{ordinal_caption_2}}",
            "image_3": "{{next_image_ref_3}}",
            "caption_3": "{{ordinal_caption_3}}",
        },
    },
)

_STYLE_FAMILY_DEFS_BY_BUILT_IN = {
    MANUAL_PUBLIC_TEMPLATE_NAME: _MANUAL_STYLE_FAMILIES,
}
_STYLE_PRESETS_BY_BUILT_IN = {
    MANUAL_PUBLIC_TEMPLATE_NAME: _MANUAL_STYLE_PRESETS,
}
_DEFAULT_PRESET_ID_BY_BUILT_IN = {
    MANUAL_PUBLIC_TEMPLATE_NAME: DEFAULT_MANUAL_STYLE_PRESET_ID,
}


def default_style_preset_id(built_in: str) -> str | None:
    return _DEFAULT_PRESET_ID_BY_BUILT_IN.get(built_in)


def get_style_preset_catalog(built_in: str) -> dict[str, object]:
    family_defs = _STYLE_FAMILY_DEFS_BY_BUILT_IN.get(built_in, ())
    preset_defs = _STYLE_PRESETS_BY_BUILT_IN.get(built_in, ())
    visible_presets = [
        deepcopy(_public_preset_fields(preset))
        for preset in sorted(preset_defs, key=_preset_sort_key)
        if preset.get("visibility") == _PUBLIC_VISIBILITY
    ]
    counts_by_family: dict[str, int] = {}
    for preset in visible_presets:
        family_id = str(preset["family_id"])
        counts_by_family[family_id] = counts_by_family.get(family_id, 0) + 1

    visible_families = []
    for family in sorted(family_defs, key=_family_sort_key):
        if family.get("visibility") != _PUBLIC_VISIBILITY:
            continue
        family_id = str(family["family_id"])
        count = counts_by_family.get(family_id, 0)
        if count <= 0:
            continue
        visible_families.append(
            {
                "family_id": family_id,
                "label": str(family["label"]),
                "order": int(family["order"]),
                "count": count,
            }
        )

    return {
        "built_in": built_in,
        "families": visible_families,
        "presets": visible_presets,
    }


def append_style_preset_to_payload_yaml(
    payload_yaml: str,
    *,
    built_in: str,
    preset_id: str | None = None,
    legacy_slide_style: str | None = None,
) -> tuple[str, dict[str, str], list[str]]:
    if built_in != MANUAL_PUBLIC_TEMPLATE_NAME:
        raise ValidationError(
            [
                "Manual slide styles can only be added when the built-in manual starter is active."
            ]
        )

    preset = _resolve_preset(
        built_in,
        preset_id=preset_id,
        legacy_slide_style=legacy_slide_style,
    )
    header, yaml_body = _split_leading_comment_block(payload_yaml)
    source_text = yaml_body or payload_yaml
    raw_data = parse_yaml_text(source_text)
    if not isinstance(raw_data, dict):
        raise ValidationError(
            ["Manual slide styles can only be appended to YAML object payloads."]
        )
    if detect_payload_kind(raw_data) != "content":
        raise ValidationError(
            ["Manual slide styles can only be appended to report_content drafts."]
        )

    wrapper_key = (
        "report_content"
        if isinstance(raw_data.get("report_content"), dict)
        else None
    )
    root = raw_data["report_content"] if wrapper_key is not None else raw_data
    slides = root.get("slides")
    if slides is None:
        slides = []
        root["slides"] = slides
    if not isinstance(slides, list):
        raise ValidationError(["Field 'slides' must be a list."])

    new_slide = _build_manual_slide_from_preset(slides, preset)
    slides.append(new_slide)
    document = {wrapper_key: root} if wrapper_key is not None else root
    rendered_yaml = serialize_document(document, fmt="yaml").strip()
    if header:
        rendered_yaml = f"{header}\n{rendered_yaml}"

    added_slide = {
        "preset_id": str(preset["preset_id"]),
        "pattern_id": str(preset["pattern_id"]),
        "label": str(preset["label"]),
        "slide_title": _derive_manual_slide_title(new_slide),
    }
    image_refs = _collect_manual_slide_image_refs(new_slide)
    hints = [
        "Review the new slide text placeholders and refresh the preview rail.",
    ]
    if image_refs:
        hints.append(
            "New screenshot refs were reserved: " + ", ".join(image_refs) + "."
        )
    return rendered_yaml, added_slide, hints


def delete_manual_slide_from_payload_yaml(
    payload_yaml: str,
    *,
    built_in: str,
    source_kind: str,
    source_slide_index: int | None = None,
) -> tuple[str, dict[str, object], list[str]]:
    if built_in != MANUAL_PUBLIC_TEMPLATE_NAME:
        raise ValidationError(
            [
                "Manual slides can only be deleted when the built-in manual starter is active."
            ]
        )

    header, yaml_body = _split_leading_comment_block(payload_yaml)
    source_text = yaml_body or payload_yaml
    raw_data = parse_yaml_text(source_text)
    if not isinstance(raw_data, dict):
        raise ValidationError(
            ["Manual slides can only be deleted from YAML object payloads."]
        )
    if detect_payload_kind(raw_data) != "content":
        raise ValidationError(
            ["Manual slides can only be deleted from report_content drafts."]
        )

    wrapper_key = (
        "report_content"
        if isinstance(raw_data.get("report_content"), dict)
        else None
    )
    root = raw_data["report_content"] if wrapper_key is not None else raw_data
    slides = root.get("slides")
    if slides is None:
        slides = []
        root["slides"] = slides
    if not isinstance(slides, list):
        raise ValidationError(["Field 'slides' must be a list."])

    if source_kind == "contents_slide":
        deleted_slide = root.pop("contents_slide", None)
        if not isinstance(deleted_slide, dict):
            raise ValidationError(
                ["The manual draft does not include a contents slide to delete."]
            )
        deleted_slide_info = {
            "source_kind": "contents_slide",
            "pattern_id": _manual_scalar_text(deleted_slide.get("pattern_id"))
            or "contents.manual",
            "slide_title": "Contents",
        }
        hints = ["The generated deck will now skip the contents slide."]
    elif source_kind == "content_slide":
        if source_slide_index is None:
            raise ValidationError(
                ["Field 'source_slide_index' is required for content slide deletion."]
            )
        if len(slides) <= 1:
            raise ValidationError(
                ["The manual draft must keep at least 1 content slide."]
            )
        if source_slide_index < 1 or source_slide_index > len(slides):
            raise ValidationError(
                [
                    f"Field 'source_slide_index' must be between 1 and {len(slides)}."
                ]
            )
        deleted_slide = slides.pop(source_slide_index - 1)
        if not isinstance(deleted_slide, dict):
            raise ValidationError(
                ["The selected manual slide could not be removed from the draft."]
            )
        deleted_slide_info = {
            "source_kind": "content_slide",
            "source_slide_index": source_slide_index,
            "pattern_id": _manual_scalar_text(deleted_slide.get("pattern_id"))
            or "manual.slide",
            "slide_title": _derive_manual_slide_title(deleted_slide),
        }
        image_refs = _collect_manual_slide_image_refs(deleted_slide)
        hints = []
        if image_refs:
            hints.append(
                "Removed screenshot refs: " + ", ".join(image_refs) + "."
            )
    else:
        raise ValidationError(
            [
                "Field 'source_kind' must be one of: contents_slide, content_slide."
            ]
        )

    document = {wrapper_key: root} if wrapper_key is not None else root
    rendered_yaml = serialize_document(document, fmt="yaml").strip()
    if header:
        rendered_yaml = f"{header}\n{rendered_yaml}"
    return rendered_yaml, deleted_slide_info, hints


def _family_sort_key(family: dict[str, object]) -> tuple[int, str]:
    return (int(family["order"]), str(family["family_id"]))


def _preset_sort_key(preset: dict[str, object]) -> tuple[int, str]:
    return (int(preset["order"]), str(preset["preset_id"]))


def _public_preset_fields(preset: dict[str, object]) -> dict[str, object]:
    return {
        "preset_id": str(preset["preset_id"]),
        "label": str(preset["label"]),
        "family_id": str(preset["family_id"]),
        "pattern_id": str(preset["pattern_id"]),
        "image_count": int(preset["image_count"]),
        "description": str(preset["description"]),
        "thumbnail": deepcopy(preset["thumbnail"]),
        "default_slot_values": deepcopy(preset["default_slot_values"]),
        "tags": list(preset["tags"]),
    }


def _resolve_preset(
    built_in: str,
    *,
    preset_id: str | None,
    legacy_slide_style: str | None,
) -> dict[str, object]:
    preset_defs = _STYLE_PRESETS_BY_BUILT_IN.get(built_in, ())
    preset_by_id = {
        str(preset["preset_id"]): preset
        for preset in preset_defs
        if preset.get("visibility") == _PUBLIC_VISIBILITY
    }
    preset_by_pattern_id = {
        str(preset["pattern_id"]): preset
        for preset in preset_defs
        if preset.get("visibility") == _PUBLIC_VISIBILITY
    }

    requested = preset_id if isinstance(preset_id, str) else legacy_slide_style
    if isinstance(requested, str):
        normalized = requested.strip()
        if normalized in preset_by_id:
            return preset_by_id[normalized]
        if normalized in preset_by_pattern_id:
            return preset_by_pattern_id[normalized]

    allowed = ", ".join(sorted(preset_by_id))
    raise ValidationError([f"Field 'preset_id' must be one of: {allowed}."])


def _split_leading_comment_block(payload_yaml: str) -> tuple[str, str]:
    lines = payload_yaml.splitlines()
    header_lines: list[str] = []
    body_start = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            header_lines.append(line)
            continue
        body_start = index
        break
    header = "\n".join(header_lines).rstrip()
    body = "\n".join(lines[body_start:]).strip()
    return header, body


def _build_manual_slide_from_preset(
    existing_slides: list[object], preset: dict[str, object]
) -> dict[str, object]:
    image_count = int(preset.get("image_count", 0))
    next_section_no = _next_manual_section_index(existing_slides)
    current_section_no = _current_manual_section_index(existing_slides)
    next_step_no = _next_manual_step_number(existing_slides, current_section_no)
    next_image_ref_index = _next_manual_image_ref_index(existing_slides)
    token_map = {
        "next_section_index": str(next_section_no),
        "current_section_index": str(current_section_no),
        "next_step_no": next_step_no,
    }
    for offset in range(image_count):
        token_map[f"next_image_ref_{offset + 1}"] = (
            f"image_{next_image_ref_index + offset}"
        )
        token_map[f"ordinal_caption_{offset + 1}"] = _ordinal_caption_label(offset + 1)

    slots = _render_template_value(
        deepcopy(preset["default_slot_values"]),
        token_map,
    )
    if not isinstance(slots, dict):
        raise ValidationError(["Style preset slots must be an object."])
    return {
        "pattern_id": str(preset["pattern_id"]),
        "slots": slots,
    }


def _render_template_value(value: Any, token_map: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _render_template_value(child, token_map)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_render_template_value(child, token_map) for child in value]
    if isinstance(value, str):
        return _TOKEN_RE.sub(
            lambda match: token_map.get(match.group("name"), match.group(0)),
            value,
        )
    return value


def _current_manual_section_index(existing_slides: list[object]) -> int:
    sections = _collect_manual_section_indices(existing_slides)
    if sections:
        return max(sections)
    return 1


def _next_manual_section_index(existing_slides: list[object]) -> int:
    sections = _collect_manual_section_indices(existing_slides)
    return (max(sections) + 1) if sections else 1


def _next_manual_step_number(existing_slides: list[object], section_index: int) -> str:
    max_step_index = 0
    for step_section, step_index in _collect_manual_step_numbers(existing_slides):
        if step_section == section_index and step_index > max_step_index:
            max_step_index = step_index
    return f"{section_index}.{max_step_index + 1}"


def _next_manual_image_ref_index(existing_slides: list[object]) -> int:
    max_index = 0
    for slide in existing_slides:
        slots = _manual_slide_slots(slide)
        for alias, raw_value in slots.items():
            if not isinstance(alias, str) or not alias.startswith("image_"):
                continue
            normalized = _manual_scalar_text(raw_value)
            if normalized is None:
                continue
            match = _MANUAL_IMAGE_REF_RE.fullmatch(normalized)
            if match is None:
                continue
            max_index = max(max_index, int(match.group("index")))
    return max_index + 1


def _collect_manual_section_indices(existing_slides: list[object]) -> list[int]:
    sections: set[int] = set()
    for slide in existing_slides:
        slots = _manual_slide_slots(slide)
        section_no = _parse_manual_section_index(slots.get("section_no"))
        if section_no is not None:
            sections.add(section_no)
        step_no = _parse_manual_step_number(slots.get("step_no"))
        if step_no is not None:
            sections.add(step_no[0])
    return sorted(sections)


def _collect_manual_step_numbers(existing_slides: list[object]) -> list[tuple[int, int]]:
    step_numbers: list[tuple[int, int]] = []
    for slide in existing_slides:
        slots = _manual_slide_slots(slide)
        step_no = _parse_manual_step_number(slots.get("step_no"))
        if step_no is not None:
            step_numbers.append(step_no)
    return step_numbers


def _manual_slide_slots(slide: object) -> dict[str, object]:
    if not isinstance(slide, dict):
        return {}
    slots = slide.get("slots")
    if not isinstance(slots, dict):
        return {}
    return slots


def _parse_manual_section_index(raw_value: object) -> int | None:
    normalized = _manual_scalar_text(raw_value)
    if normalized is None:
        return None
    match = _MANUAL_SECTION_NO_RE.fullmatch(normalized)
    if match is None:
        return None
    return int(match.group("section"))


def _parse_manual_step_number(raw_value: object) -> tuple[int, int] | None:
    normalized = _manual_scalar_text(raw_value)
    if normalized is None:
        return None
    match = _MANUAL_STEP_NO_RE.fullmatch(normalized)
    if match is None:
        return None
    return (int(match.group("section")), int(match.group("step")))


def _manual_scalar_text(raw_value: object) -> str | None:
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return normalized or None
    if isinstance(raw_value, bool):
        return "true" if raw_value else "false"
    if isinstance(raw_value, int):
        return str(raw_value)
    if isinstance(raw_value, float):
        if raw_value.is_integer():
            return str(int(raw_value))
        return format(raw_value, "g")
    return None


def _ordinal_caption_label(index: int) -> str:
    if index == 1:
        return "First screenshot caption"
    if index == 2:
        return "Second screenshot caption"
    if index == 3:
        return "Third screenshot caption"
    return f"Screenshot {index} caption"


def _derive_manual_slide_title(slide: dict[str, object]) -> str:
    slots = _manual_slide_slots(slide)
    if "section_no" in slots and "section_title" in slots:
        return _manual_join_title_parts(slots["section_no"], slots["section_title"])
    if "step_no" in slots and "step_title" in slots:
        return _manual_join_title_parts(slots["step_no"], slots["step_title"])
    normalized_pattern_id = _manual_scalar_text(slide.get("pattern_id"))
    if normalized_pattern_id is not None:
        return normalized_pattern_id
    return "New Slide"


def _collect_manual_slide_image_refs(slide: dict[str, object]) -> list[str]:
    refs: list[str] = []
    for alias, raw_value in _manual_slide_slots(slide).items():
        if not isinstance(alias, str) or not alias.startswith("image_"):
            continue
        normalized = _manual_scalar_text(raw_value)
        if normalized is not None:
            refs.append(normalized)
    return refs


def _manual_join_title_parts(prefix: object, label: object) -> str:
    normalized_prefix = _manual_scalar_text(prefix) or ""
    normalized_label = _manual_scalar_text(label) or ""
    return f"{normalized_prefix} {normalized_label}".strip()
