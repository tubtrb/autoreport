"""Tests for the contract-first Autoreport CLI."""

from __future__ import annotations

import base64
import io
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from uuid import uuid4

from pptx import Presentation
import yaml

from autoreport.cli import main
from autoreport.template_flow import get_built_in_contract, scaffold_payload


TEST_TEMP_ROOT = Path("tests") / "_tmp"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)


def make_test_dir() -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


def write_authoring_payload(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            scaffold_payload(get_built_in_contract()).to_dict(),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def write_runtime_payload(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "report_payload:",
                "  payload_version: autoreport.payload.v1",
                "  template_id: autoreport-editorial-v1",
                "  title_slide:",
                "    title: Autoreport",
                "    subtitle:",
                "      - Template-aware PPTX autofill engine",
                "  contents:",
                "    enabled: true",
                "  slides:",
                "    - kind: text",
                "      title: What It Does",
                "      include_in_contents: true",
                "      body:",
                "        - Generate editable PowerPoint decks.",
                "      slot_overrides: {}",
            ]
        ),
        encoding="utf-8",
    )


def write_report_content(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "report_content:",
                "  title_slide:",
                "    pattern_id: cover.editorial",
                "    slots:",
                "      title: Autoreport",
                "      subtitle_1: |",
                "        Template-aware PPTX autofill engine",
                "  contents_slide:",
                "    pattern_id: contents.editorial",
                "    slots:",
                "      title: Contents",
                "      body_1: |",
                "        1. What It Does",
                "  slides:",
                "    - pattern_id: text.editorial",
                "      slots:",
                "        title: What It Does",
                "        body_1: |",
                "          Generate editable PowerPoint decks.",
            ]
        ),
        encoding="utf-8",
    )


def build_manual_authoring_payload_with_paths(image_paths: list[Path]) -> dict[str, object]:
    payload = scaffold_payload(
        get_built_in_contract("autoreport_manual")
    ).to_dict()
    image_iter = iter(image_paths)
    for slide in payload["authoring_payload"]["slides"]:
        for image in slide.get("assets", {}).get("images", []):
            image.pop("ref", None)
            image["path"] = str(next(image_iter))
    return payload


def write_manual_authoring_payload(path: Path, *, image_paths: list[Path]) -> None:
    path.write_text(
        yaml.safe_dump(
            build_manual_authoring_payload_with_paths(image_paths),
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def write_manual_report_content(path: Path, *, image_paths: list[Path]) -> None:
    payload = {
        "report_content": {
            "title_slide": {
                "pattern_id": "cover.manual",
                "slots": {
                    "doc_title": "Autoreport PowerPoint User Guide",
                    "doc_subtitle": "CLI manual compile smoke",
                "doc_version": "v0.4.2",
                    "author_or_owner": "Autoreport Team",
                },
            },
            "contents_slide": {
                "pattern_id": "contents.manual",
                "slots": {
                    "contents_title": "Contents",
                    "contents_group_label": "Procedure Overview",
                },
            },
            "slides": [
                {
                    "pattern_id": "text.manual.section_break",
                    "slots": {
                        "section_no": "1.",
                        "section_title": "Choose A Starter Template",
                        "section_subtitle": "Start with the built-in editorial or manual starter first.",
                    },
                },
                {
                    "pattern_id": "text_image.manual.procedure.one",
                    "slots": {
                        "step_no": "1.1",
                        "step_title": "Review The Starter Example",
                        "command_or_action": "Action: open the starter example and confirm the selected template.",
                        "summary": "Capture the starting editor state.",
                        "detail_body": "Review the starter YAML before continuing.",
                        "image_1": str(image_paths[0]),
                        "caption_1": "Starter example loaded",
                    },
                },
                {
                    "pattern_id": "text_image.manual.procedure.two",
                    "slots": {
                        "step_no": "1.2",
                        "step_title": "Customize The Draft",
                        "command_or_action": "Action: edit the YAML title, sections, and example copy.",
                        "summary": "Compare before and after edits.",
                        "detail_body": "Update the guide text and confirm the changes.",
                        "image_1": str(image_paths[1]),
                        "image_2": str(image_paths[2]),
                        "caption_1": "Starter YAML before editing",
                        "caption_2": "Starter YAML after editing",
                    },
                },
                {
                    "pattern_id": "text_image.manual.procedure.three",
                    "slots": {
                        "step_no": "1.3",
                        "step_title": "Generate The PowerPoint",
                        "command_or_action": "Action: refresh the slide order and generate the PowerPoint deck.",
                        "summary": "Capture preview, generation, and download states.",
                        "detail_body": "Confirm the deck preview and download complete successfully.",
                        "image_1": str(image_paths[3]),
                        "image_2": str(image_paths[4]),
                        "image_3": str(image_paths[5]),
                        "caption_1": "Slide preview ready",
                        "caption_2": "Generation in progress",
                        "caption_3": "PowerPoint download complete",
                    },
                },
            ],
        }
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


class CLITestCase(unittest.TestCase):
    """Verify CLI generation and authoring-first command flows."""

    def test_inspect_template_command_prints_built_in_contract(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(["inspect-template", "--built-in", "autoreport_editorial"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("template_contract:", stdout_buffer.getvalue())
        self.assertIn("template_id: autoreport-editorial-v1", stdout_buffer.getvalue())
        self.assertIn("image_layout: horizontal", stdout_buffer.getvalue())

    def test_inspect_template_command_prints_manual_built_in_contract(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(["inspect-template", "--built-in", "autoreport_manual"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("template_id: autoreport-manual-v1", stdout_buffer.getvalue())
        self.assertIn("pattern_id: cover.manual", stdout_buffer.getvalue())
        self.assertIn("pattern_id: text_image.manual.procedure.three", stdout_buffer.getvalue())

    def test_scaffold_payload_command_writes_authoring_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            contract_path = test_dir / "contract.yaml"
            contract_path.write_text(
                yaml.safe_dump(
                    get_built_in_contract().to_dict(),
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["scaffold-payload", str(contract_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("authoring_payload:", stdout_buffer.getvalue())
        self.assertIn("layout_request:", stdout_buffer.getvalue())
        self.assertIn("template_id: autoreport-editorial-v1", stdout_buffer.getvalue())

    def test_scaffold_payload_command_writes_manual_authoring_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            contract_path = test_dir / "manual_contract.yaml"
            contract_path.write_text(
                yaml.safe_dump(
                    get_built_in_contract("autoreport_manual").to_dict(),
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["scaffold-payload", str(contract_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("template_id: autoreport-manual-v1", stdout_buffer.getvalue())
        self.assertIn("pattern_id: text.manual.section_break", stdout_buffer.getvalue())
        self.assertIn("slot_values:", stdout_buffer.getvalue())

    def test_compile_payload_command_emits_runtime_report_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "authoring.yaml"
            write_authoring_payload(payload_path)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["compile-payload", str(payload_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("report_payload:", stdout_buffer.getvalue())
        self.assertIn("pattern_id: text.editorial", stdout_buffer.getvalue())

    def test_compile_payload_command_accepts_report_content_draft(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "report_content.yaml"
            write_report_content(payload_path)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["compile-payload", str(payload_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("report_payload:", stdout_buffer.getvalue())
        self.assertIn("pattern_id: text.editorial", stdout_buffer.getvalue())

    def test_compile_payload_command_accepts_fenced_report_content_draft(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "report_content_fenced.yaml"
            raw_path = test_dir / "report_content_raw.yaml"
            write_report_content(raw_path)
            payload_path.write_text(
                f"```yaml\n{raw_path.read_text(encoding='utf-8')}\n```",
                encoding="utf-8",
            )

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["compile-payload", str(payload_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("report_payload:", stdout_buffer.getvalue())
        self.assertIn("pattern_id: text.editorial", stdout_buffer.getvalue())

    def test_compile_payload_command_accepts_manual_report_content_draft(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "manual_report_content.yaml"
            image_paths = []
            for index in range(1, 7):
                image_path = test_dir / f"manual_{index}.png"
                image_path.write_bytes(PNG_BYTES)
                image_paths.append(image_path)
            write_manual_report_content(payload_path, image_paths=image_paths)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    ["compile-payload", str(payload_path), "--built-in", "autoreport_manual"]
                )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("report_payload:", stdout_buffer.getvalue())
        self.assertIn("template_id: autoreport-manual-v1", stdout_buffer.getvalue())
        self.assertIn("pattern_id: text.manual.section_break", stdout_buffer.getvalue())
        self.assertIn(
            "pattern_id: text_image.manual.procedure.three",
            stdout_buffer.getvalue(),
        )

    def test_generate_command_writes_presentation_from_authoring_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "payload.yaml"
            output_path = test_dir / "autoreport_demo.pptx"
            write_authoring_payload(payload_path)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        str(payload_path),
                        "--output",
                        str(output_path),
                    ]
                )
            output_exists = output_path.exists()
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout_buffer.getvalue().splitlines(),
            [f"Autoreport deck generated successfully: {output_path}"],
        )
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertTrue(output_exists)

    def test_generate_command_still_accepts_legacy_runtime_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "runtime_payload.yaml"
            output_path = test_dir / "autoreport_demo.pptx"
            write_runtime_payload(payload_path)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        str(payload_path),
                        "--output",
                        str(output_path),
                    ]
                )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_generate_command_accepts_report_content_draft(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "report_content.yaml"
            output_path = test_dir / "autoreport_demo.pptx"
            write_report_content(payload_path)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        str(payload_path),
                        "--output",
                        str(output_path),
                    ]
                )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_generate_command_writes_manual_presentation_from_authoring_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "manual_authoring.yaml"
            output_path = test_dir / "manual_demo.pptx"
            image_paths = []
            for index in range(1, 7):
                image_path = test_dir / f"manual_{index}.png"
                image_path.write_bytes(PNG_BYTES)
                image_paths.append(image_path)
            write_manual_authoring_payload(payload_path, image_paths=image_paths)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        str(payload_path),
                        "--built-in",
                        "autoreport_manual",
                        "--output",
                        str(output_path),
                    ]
                )
            presentation = Presentation(str(output_path))
            output_exists = output_path.exists()
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertTrue(output_exists)
        self.assertEqual(len(presentation.slides), 6)

    def test_generate_command_reports_validation_errors(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "invalid_payload.yaml"
            payload_path.write_text(
                "\n".join(
                    [
                        "authoring_payload:",
                        "  payload_version: autoreport.authoring.v1",
                        "  template_id: autoreport-editorial-v1",
                        "  title_slide:",
                        "    title: '  '",
                        "    subtitle: []",
                        "  contents:",
                        "    enabled: true",
                        "  slides: []",
                    ]
                ),
                encoding="utf-8",
            )

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["generate", str(payload_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("Payload validation failed.", stderr_buffer.getvalue())
        self.assertIn("Field 'title_slide.title' must be a non-empty string.", stderr_buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
