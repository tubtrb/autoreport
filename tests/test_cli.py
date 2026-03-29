"""Tests for the contract-first Autoreport CLI."""

from __future__ import annotations

import io
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from uuid import uuid4

import yaml

from autoreport.cli import main
from autoreport.template_flow import get_built_in_contract, scaffold_payload


TEST_TEMP_ROOT = Path("tests") / "_tmp"


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
