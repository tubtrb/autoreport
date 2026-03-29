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
from autoreport.template_flow import inspect_template_contract, scaffold_payload


TEST_TEMP_ROOT = Path("tests") / "_tmp"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)


def make_test_dir() -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


def build_authoring_payload(
    *,
    image_paths: list[Path] | None = None,
    image_orientation: str = "auto",
    include_contents: bool = True,
) -> dict[str, object]:
    payload = scaffold_payload(
        inspect_template_contract(built_in="autoreport_editorial"),
        include_text_image=(image_paths is not None),
    ).to_dict()
    if image_paths is None:
        payload["authoring_payload"]["contents"]["enabled"] = include_contents
        return payload

    payload["authoring_payload"]["contents"]["enabled"] = include_contents
    text_image_slide = payload["authoring_payload"]["slides"][2]
    text_image_slide["context"]["summary"] = "Compare visuals against the authored narrative."
    text_image_slide["assets"]["images"] = [
        {"path": str(path), "fit": "contain"} for path in image_paths
    ]
    text_image_slide["layout_request"]["image_count"] = len(image_paths)
    text_image_slide["layout_request"]["image_orientation"] = image_orientation
    return payload


def build_runtime_text_image_payload(
    *,
    image_path: Path,
    text_image_body: list[str],
) -> dict[str, object]:
    return {
        "report_payload": {
            "payload_version": "autoreport.payload.v1",
            "template_id": "autoreport-editorial-v1",
            "title_slide": {
                "title": "Autoreport",
                "subtitle": ["Template-aware PPTX autofill engine"],
            },
            "contents": {"enabled": True},
            "slides": [
                {
                    "kind": "text_image",
                    "title": "Why It Matters",
                    "include_in_contents": True,
                    "body": text_image_body,
                    "image": {"path": str(image_path), "fit": "contain"},
                    "caption": "Workflow preview",
                    "slot_overrides": {},
                }
            ],
        }
    }


def build_text_image_spill_body() -> list[str]:
    return [
        (
            f"Bullet {index}: template-aware autofill keeps editorial structure "
            "stable while long narrative content spills onto a continuation slide "
            "for release inspection."
        )
        for index in range(1, 11)
    ]


class GeneratorTestCase(unittest.TestCase):
    """Verify contract-first generation creates the expected PowerPoint structure."""

    def test_prepare_generation_artifacts_exposes_editorial_contract(self) -> None:
        artifacts = prepare_generation_artifacts_from_mapping(
            build_authoring_payload(),
            presentation=Presentation(),
        )

        self.assertEqual(artifacts.template_contract.template_id, "autoreport-editorial-v1")
        self.assertEqual(
            [pattern.pattern_id for pattern in artifacts.template_contract.slide_patterns],
            [
                "text.editorial",
                "metrics.editorial",
                "text_image.editorial",
                "text_image.editorial.two_horizontal",
                "text_image.editorial.two_vertical",
                "text_image.editorial.three_horizontal",
                "text_image.editorial.three_vertical",
            ],
        )
        self.assertEqual(
            [slide.slide_title for slide in artifacts.fill_plan.slides],
            ["Autoreport", "Contents", "What It Does", "Adoption Snapshot"],
        )
        self.assertEqual(len(artifacts.diagnostic_report.errors), 0)

    def test_generate_report_from_mapping_creates_editorial_presentation_from_authoring_payload(self) -> None:
        test_dir = make_test_dir()
        try:
            output_path = test_dir / "output" / "autoreport_demo.pptx"
            generated_path = generate_report_from_mapping(
                build_authoring_payload(),
                output_path=output_path,
            )
            presentation = Presentation(str(output_path))
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(generated_path, output_path)
        self.assertEqual(len(presentation.slides), 4)

    def test_generate_report_from_mapping_supports_single_image_authoring(self) -> None:
        test_dir = make_test_dir()
        try:
            image_path = test_dir / "workflow.png"
            image_path.write_bytes(PNG_BYTES)
            output_path = test_dir / "output" / "autoreport_text_image.pptx"

            generate_report_from_mapping(
                build_authoring_payload(image_paths=[image_path]),
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

    def test_generate_report_from_mapping_supports_two_horizontal_images(self) -> None:
        test_dir = make_test_dir()
        try:
            image_paths = []
            for name in ("one.png", "two.png"):
                path = test_dir / name
                path.write_bytes(PNG_BYTES)
                image_paths.append(path)
            output_path = test_dir / "output" / "autoreport_two_horizontal.pptx"

            generate_report_from_mapping(
                build_authoring_payload(
                    image_paths=image_paths,
                    image_orientation="horizontal",
                ),
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
        self.assertEqual(len(image_shapes), 2)

    def test_generate_report_from_mapping_supports_three_vertical_images(self) -> None:
        test_dir = make_test_dir()
        try:
            image_paths = []
            for name in ("one.png", "two.png", "three.png"):
                path = test_dir / name
                path.write_bytes(PNG_BYTES)
                image_paths.append(path)
            output_path = test_dir / "output" / "autoreport_three_vertical.pptx"

            generate_report_from_mapping(
                build_authoring_payload(
                    image_paths=image_paths,
                    image_orientation="vertical",
                    include_contents=False,
                ),
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

        self.assertEqual(len(presentation.slides), 4)
        self.assertEqual(len(image_shapes), 3)

    def test_runtime_text_image_continuation_does_not_repeat_media(self) -> None:
        test_dir = make_test_dir()
        try:
            image_path = test_dir / "workflow.png"
            image_path.write_bytes(PNG_BYTES)
            artifacts = prepare_generation_artifacts_from_mapping(
                build_runtime_text_image_payload(
                    image_path=image_path,
                    text_image_body=build_text_image_spill_body(),
                ),
                presentation=Presentation(),
            )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        text_image_slides = [
            slide
            for slide in artifacts.generation_summary.slides
            if slide.kind == "text_image"
        ]

        self.assertEqual(
            [slide.slide_title for slide in text_image_slides],
            ["Why It Matters", "Why It Matters (cont.)"],
        )
        self.assertEqual(text_image_slides[0].image_slot_names, ("text_image.image_1",))
        self.assertEqual(text_image_slides[1].image_slot_names, ())

    def test_generate_report_uses_payload_file_and_default_output_directory(self) -> None:
        test_dir = make_test_dir()
        previous_cwd = Path.cwd()
        try:
            payload_path = (test_dir / "autoreport_payload.yaml").resolve()
            payload_path.write_text(
                __import__("yaml").safe_dump(
                    build_authoring_payload(),
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
