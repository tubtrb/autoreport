"""Tests for contract-first generation and template inspection."""

from __future__ import annotations

import base64
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from pptx import Presentation

from autoreport.engine.generator import (
    generate_report,
    generate_report_from_mapping,
    prepare_generation_artifacts_from_mapping,
)
from autoreport.models import ReportRequest
from autoreport.template_flow import inspect_template_contract


TEST_TEMP_ROOT = Path("tests") / "_tmp"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)


def make_test_dir() -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


def build_payload(*, include_text_image: bool = False, image_path: Path | None = None) -> dict[str, object]:
    slides: list[dict[str, object]] = [
        {
            "kind": "text",
            "title": "What It Does",
            "include_in_contents": True,
            "body": [
                "Generate editable PowerPoint decks from structured inputs.",
                "Fill template slots instead of rebuilding layouts.",
            ],
            "slot_overrides": {},
        },
        {
            "kind": "metrics",
            "title": "Adoption Snapshot",
            "include_in_contents": True,
            "items": [
                {"label": "Templates profiled", "value": 12},
                {"label": "Decks generated", "value": 24},
            ],
            "slot_overrides": {},
        },
    ]
    if include_text_image:
        slides.append(
            {
                "kind": "text_image",
                "title": "Why It Matters",
                "include_in_contents": True,
                "body": ["Teams keep their own brand language."],
                "image": {"path": str(image_path), "fit": "contain"},
                "caption": "Workflow preview",
                "slot_overrides": {},
            }
        )
    return {
        "report_payload": {
            "payload_version": "autoreport.payload.v1",
            "template_id": "autoreport-editorial-v1",
            "title_slide": {
                "title": "Autoreport",
                "subtitle": ["Template-aware PPTX autofill engine"],
            },
            "contents": {"enabled": True},
            "slides": slides,
        }
    }


class GeneratorTestCase(unittest.TestCase):
    """Verify contract-first generation creates the expected PowerPoint structure."""

    def test_prepare_generation_artifacts_exposes_editorial_contract(self) -> None:
        artifacts = prepare_generation_artifacts_from_mapping(
            build_payload(),
            presentation=Presentation(),
        )

        self.assertEqual(artifacts.template_contract.template_id, "autoreport-editorial-v1")
        self.assertEqual(
            [pattern.kind for pattern in artifacts.template_contract.slide_patterns],
            ["text", "metrics", "text_image"],
        )
        self.assertEqual(
            [slide.slide_title for slide in artifacts.fill_plan.slides],
            ["Autoreport", "Contents", "What It Does", "Adoption Snapshot"],
        )
        self.assertEqual(len(artifacts.diagnostic_report.errors), 0)

    def test_generate_report_from_mapping_creates_editorial_presentation(self) -> None:
        test_dir = make_test_dir()
        try:
            output_path = test_dir / "output" / "autoreport_demo.pptx"
            generated_path = generate_report_from_mapping(
                build_payload(),
                output_path=output_path,
            )
            presentation = Presentation(str(output_path))
            slide_texts = [
                "\n".join(
                    shape.text
                    for shape in slide.shapes
                    if hasattr(shape, "text") and shape.text
                )
                for slide in presentation.slides
            ]
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(generated_path, output_path)
        self.assertEqual(len(presentation.slides), 4)
        self.assertIn("Autoreport", "\n".join(slide_texts))
        self.assertGreater(len(presentation.slides[0].shapes), 2)
        self.assertGreater(len(presentation.slides[2].shapes), 2)

    def test_generate_report_from_mapping_supports_text_image_slides(self) -> None:
        test_dir = make_test_dir()
        try:
            image_path = test_dir / "workflow.png"
            image_path.write_bytes(PNG_BYTES)
            output_path = test_dir / "output" / "autoreport_text_image.pptx"

            generate_report_from_mapping(
                build_payload(include_text_image=True, image_path=image_path),
                output_path=output_path,
            )
            presentation = Presentation(str(output_path))
            image_shapes = [
                shape
                for shape in presentation.slides[-1].shapes
                if hasattr(shape, "image")
            ]
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(len(presentation.slides), 5)
        self.assertGreaterEqual(len(image_shapes), 1)

    def test_generate_report_uses_payload_file_and_default_output_directory(self) -> None:
        test_dir = make_test_dir()
        previous_cwd = Path.cwd()
        try:
            payload_path = (test_dir / "autoreport_payload.yaml").resolve()
            payload_path.write_text(
                __import__("yaml").safe_dump(
                    build_payload(),
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            expected_output_path = (test_dir / "output" / "autoreport_payload.pptx").resolve()

            __import__("os").chdir(test_dir)
            generated_path = generate_report(ReportRequest(source_path=payload_path))
            generated_exists = expected_output_path.exists()
        finally:
            __import__("os").chdir(previous_cwd)
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(generated_path, Path("output") / "autoreport_payload.pptx")
        self.assertTrue(generated_exists)

    def test_user_template_is_profiled_into_the_same_contract_family(self) -> None:
        test_dir = make_test_dir()
        try:
            template_path = test_dir / "sample-template.pptx"
            Presentation().save(str(template_path))
            contract = inspect_template_contract(template_path=template_path)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(contract.template_source, "user_template")
        self.assertIn("text", [pattern.kind for pattern in contract.slide_patterns])
        self.assertIn("metrics", [pattern.kind for pattern in contract.slide_patterns])
        self.assertIn("text_image", [pattern.kind for pattern in contract.slide_patterns])


if __name__ == "__main__":
    unittest.main()
