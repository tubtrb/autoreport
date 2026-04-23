"""Shared manual procedure layout variants for the built-in manual template."""

from __future__ import annotations


_MANUAL_PUBLIC_VISIBILITY = "public"
_MANUAL_ONE_IMAGE_FAMILY_ID = "one-image"
_MANUAL_ONE_IMAGE_TAGS = ("1 Image", "Procedure")
_MANUAL_ONE_IMAGE_DEFAULT_SLOT_VALUES = {
    "step_no": "{{next_step_no}}",
    "step_title": "New Procedure Step",
    "command_or_action": "Action: describe the command or action for this step.",
    "summary": "Short outcome summary for the step.",
    "detail_body": "Explain the detailed procedure here.",
    "image_1": "{{next_image_ref_1}}",
    "caption_1": "{{ordinal_caption_1}}",
}


def _manual_thumbnail(*blocks: dict[str, object]) -> dict[str, object]:
    return {
        "background": "#f7fafc",
        "blocks": [
            {"type": "rect", "role": "accent", "x": 8, "y": 12, "w": 4, "h": 76, "radius": 8},
            *blocks,
        ],
    }


def _manual_procedure_variant(
    *,
    pattern_id: str,
    preset_id: str,
    label: str,
    description: str,
    order: int,
    body_region: tuple[float, float, float, float],
    image_regions: tuple[tuple[float, float, float, float], ...],
    caption_regions: tuple[tuple[float, float, float, float], ...],
    thumbnail_blocks: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "preset_id": preset_id,
        "label": label,
        "family_id": _MANUAL_ONE_IMAGE_FAMILY_ID,
        "pattern_id": pattern_id,
        "image_count": 1,
        "description": description,
        "tags": _MANUAL_ONE_IMAGE_TAGS,
        "visibility": _MANUAL_PUBLIC_VISIBILITY,
        "order": order,
        "thumbnail": _manual_thumbnail(*thumbnail_blocks),
        "default_slot_values": dict(_MANUAL_ONE_IMAGE_DEFAULT_SLOT_VALUES),
        "body_region": body_region,
        "image_regions": image_regions,
        "caption_regions": caption_regions,
    }


MANUAL_PROCEDURE_VARIANTS = (
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.one",
        preset_id="manual.procedure.one",
        label="Text Left, Image Right",
        description="Pair one screenshot with text on the left.",
        order=20,
        body_region=(0.083, 0.372, 0.532, 0.330),
        image_regions=((0.664, 0.214, 0.260, 0.408),),
        caption_regions=((0.664, 0.654, 0.260, 0.066),),
        thumbnail_blocks=(
            {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 36, "h": 9, "radius": 6},
            {"type": "rect", "role": "text", "x": 18, "y": 34, "w": 30, "h": 7, "radius": 5},
            {"type": "rect", "role": "text", "x": 18, "y": 48, "w": 26, "h": 7, "radius": 5},
            {"type": "rect", "role": "image", "x": 58, "y": 18, "w": 24, "h": 56, "radius": 10},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.image_left_text_right",
        preset_id="manual.procedure.image_left_text_right",
        label="Image Left, Text Right",
        description="Pair one screenshot with text on the right.",
        order=21,
        body_region=(0.385, 0.372, 0.532, 0.330),
        image_regions=((0.083, 0.214, 0.260, 0.408),),
        caption_regions=((0.083, 0.654, 0.260, 0.066),),
        thumbnail_blocks=(
            {"type": "rect", "role": "image", "x": 18, "y": 18, "w": 24, "h": 56, "radius": 10},
            {"type": "rect", "role": "text", "x": 50, "y": 18, "w": 32, "h": 9, "radius": 6},
            {"type": "rect", "role": "text", "x": 50, "y": 34, "w": 30, "h": 7, "radius": 5},
            {"type": "rect", "role": "text", "x": 50, "y": 48, "w": 26, "h": 7, "radius": 5},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.text_top_image_left",
        preset_id="manual.procedure.text_top_image_left",
        label="Text Top, Image Left",
        description="Place the explanation above a lower-left screenshot.",
        order=22,
        body_region=(0.083, 0.372, 0.841, 0.194),
        image_regions=((0.083, 0.620, 0.377, 0.198),),
        caption_regions=((0.083, 0.838, 0.377, 0.048),),
        thumbnail_blocks=(
            {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 56, "h": 10, "radius": 6},
            {"type": "rect", "role": "image", "x": 18, "y": 48, "w": 24, "h": 22, "radius": 10},
            {"type": "rect", "role": "text", "x": 50, "y": 48, "w": 32, "h": 22, "radius": 6},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.text_top_image_right",
        preset_id="manual.procedure.text_top_image_right",
        label="Text Top, Image Right",
        description="Place the explanation above a lower-right screenshot.",
        order=23,
        body_region=(0.083, 0.372, 0.841, 0.194),
        image_regions=((0.548, 0.620, 0.377, 0.198),),
        caption_regions=((0.548, 0.838, 0.377, 0.048),),
        thumbnail_blocks=(
            {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 56, "h": 10, "radius": 6},
            {"type": "rect", "role": "text", "x": 18, "y": 48, "w": 32, "h": 22, "radius": 6},
            {"type": "rect", "role": "image", "x": 50, "y": 48, "w": 24, "h": 22, "radius": 10},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.image_left_tall_text_right",
        preset_id="manual.procedure.image_left_tall_text_right",
        label="Image Left Tall",
        description="Use a tall screenshot column on the left with text on the right.",
        order=24,
        body_region=(0.485, 0.372, 0.414, 0.330),
        image_regions=((0.083, 0.214, 0.377, 0.530),),
        caption_regions=((0.083, 0.764, 0.377, 0.058),),
        thumbnail_blocks=(
            {"type": "rect", "role": "image", "x": 18, "y": 18, "w": 28, "h": 60, "radius": 10},
            {"type": "rect", "role": "text", "x": 52, "y": 18, "w": 28, "h": 10, "radius": 6},
            {"type": "rect", "role": "text", "x": 52, "y": 36, "w": 28, "h": 8, "radius": 5},
            {"type": "rect", "role": "text", "x": 52, "y": 52, "w": 28, "h": 8, "radius": 5},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.text_left_tall_image_right",
        preset_id="manual.procedure.text_left_tall_image_right",
        label="Image Right Tall",
        description="Use a tall screenshot column on the right with text on the left.",
        order=25,
        body_region=(0.083, 0.372, 0.414, 0.330),
        image_regions=((0.548, 0.214, 0.377, 0.530),),
        caption_regions=((0.548, 0.764, 0.377, 0.058),),
        thumbnail_blocks=(
            {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 28, "h": 10, "radius": 6},
            {"type": "rect", "role": "text", "x": 18, "y": 36, "w": 28, "h": 8, "radius": 5},
            {"type": "rect", "role": "text", "x": 18, "y": 52, "w": 28, "h": 8, "radius": 5},
            {"type": "rect", "role": "image", "x": 52, "y": 18, "w": 28, "h": 60, "radius": 10},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.text_top_image_bottom",
        preset_id="manual.procedure.text_top_image_bottom",
        label="Text Top, Image Bottom",
        description="Stack the explanation above a full-width screenshot.",
        order=26,
        body_region=(0.083, 0.372, 0.841, 0.188),
        image_regions=((0.083, 0.622, 0.841, 0.196),),
        caption_regions=((0.083, 0.838, 0.841, 0.048),),
        thumbnail_blocks=(
            {"type": "rect", "role": "text", "x": 18, "y": 18, "w": 56, "h": 10, "radius": 6},
            {"type": "rect", "role": "image", "x": 18, "y": 48, "w": 64, "h": 22, "radius": 10},
        ),
    ),
    _manual_procedure_variant(
        pattern_id="text_image.manual.procedure.image_top_text_bottom",
        preset_id="manual.procedure.image_top_text_bottom",
        label="Image Top, Text Bottom",
        description="Stack a full-width screenshot above the explanation.",
        order=27,
        body_region=(0.083, 0.622, 0.841, 0.188),
        image_regions=((0.083, 0.214, 0.841, 0.330),),
        caption_regions=((0.083, 0.566, 0.841, 0.048),),
        thumbnail_blocks=(
            {"type": "rect", "role": "image", "x": 18, "y": 18, "w": 64, "h": 22, "radius": 10},
            {"type": "rect", "role": "text", "x": 18, "y": 48, "w": 56, "h": 10, "radius": 6},
        ),
    ),
)

MANUAL_PROCEDURE_PATTERN_IDS = tuple(variant["pattern_id"] for variant in MANUAL_PROCEDURE_VARIANTS)
MANUAL_PROCEDURE_PRESET_IDS = tuple(variant["preset_id"] for variant in MANUAL_PROCEDURE_VARIANTS)
MANUAL_PROCEDURE_PATTERN_IDS_BY_IMAGE_COUNT = {
    0: ("text.manual.section_break",),
    1: MANUAL_PROCEDURE_PATTERN_IDS,
    2: ("text_image.manual.procedure.two",),
    3: ("text_image.manual.procedure.three",),
}
MANUAL_ALLOWED_BODY_PATTERN_IDS = tuple(
    pattern_id
    for image_count in (0, 1, 2, 3)
    for pattern_id in MANUAL_PROCEDURE_PATTERN_IDS_BY_IMAGE_COUNT[image_count]
)
