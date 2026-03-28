"""Shared contract-export and payload-scaffold helpers for Autoreport."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import yaml

from autoreport.loader import load_yaml
from autoreport.models import (
    ContentsSettings,
    ImageSpec,
    MetricItem,
    PayloadSlide,
    ReportPayload,
    REPORT_PAYLOAD_VERSION,
    TemplateContract,
    TitleSlidePayload,
)
from autoreport.outputs.pptx_writer import PowerPointWriter
from autoreport.templates.weekly_report import (
    BASIC_TEMPLATE_NAME,
    export_template_contract,
    profile_template,
)
from autoreport.validator import validate_template_contract


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


def scaffold_payload(contract: TemplateContract) -> ReportPayload:
    """Return a starter payload for a validated template contract."""

    slides: list[PayloadSlide] = [
        PayloadSlide(
            kind="text",
            title="What It Does",
            body=[
                "Generate editable PowerPoint decks from structured inputs.",
                "Fill template slots instead of rebuilding layouts from scratch.",
            ],
        )
    ]

    if any(pattern.kind == "metrics" for pattern in contract.slide_patterns):
        slides.append(
            PayloadSlide(
                kind="metrics",
                title="Adoption Snapshot",
                items=[
                    MetricItem(label="Templates profiled", value=12),
                    MetricItem(label="Decks generated", value=24),
                ],
            )
        )

    if any(pattern.kind == "text_image" for pattern in contract.slide_patterns):
        slides.append(
            PayloadSlide(
                kind="text_image",
                title="Why It Matters",
                body=[
                    "Teams keep their own template language.",
                    "Autoreport handles fit, spill, and consistency.",
                ],
                image=ImageSpec(ref="image_1", fit="contain"),
                caption="Upload an image and reference it with image_1.",
            )
        )

    return ReportPayload(
        payload_version=REPORT_PAYLOAD_VERSION,
        template_id=contract.template_id,
        title_slide=TitleSlidePayload(
            title="Autoreport",
            subtitle=["Template-aware PPTX autofill engine"],
        ),
        contents=ContentsSettings(enabled=True),
        slides=slides,
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
