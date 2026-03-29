"""Shared demo payload helpers for the branch-local PptxGenJS spike."""

from __future__ import annotations

from pathlib import Path

from autoreport.models import TemplateContract
from autoreport.template_flow import scaffold_payload


PROTOTYPE_ROOT = Path(__file__).resolve().parent
DEFAULT_IMAGE_REFS = {
    "image_1": PROTOTYPE_ROOT / "assets" / "landscape.png",
}


def build_demo_payload_document(
    contract: TemplateContract,
) -> tuple[dict[str, object], dict[str, Path]]:
    """Return a contract-compatible demo payload plus any required image refs."""

    payload = scaffold_payload(
        contract,
        include_text_image=any(
            pattern.kind == "text_image"
            for pattern in contract.slide_patterns
        ),
    )
    image_refs = {
        ref: path
        for ref, path in DEFAULT_IMAGE_REFS.items()
        if any(
            any(
                image.ref == ref
                for image in slide.assets.images
            )
            for slide in payload.slides
        )
    }
    return payload.to_dict(), image_refs
