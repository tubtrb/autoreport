"""Tests for the contract-first Autoreport CLI."""

from __future__ import annotations

import io
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from uuid import uuid4

from autoreport.cli import main
from autoreport.template_flow import get_built_in_contract


TEST_TEMP_ROOT = Path("tests") / "_tmp"


def make_test_dir() -> Path:
    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


def write_payload(path: Path) -> None:
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


class CLITestCase(unittest.TestCase):
    """Verify CLI generation and new contract-first command flows."""

    def test_inspect_template_command_prints_built_in_contract(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(["inspect-template", "--built-in", "autoreport_editorial"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertIn("template_contract:", stdout_buffer.getvalue())
        self.assertIn("template_id: autoreport-editorial-v1", stdout_buffer.getvalue())

    def test_scaffold_payload_command_writes_starter_payload(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            contract_path = test_dir / "contract.yaml"
            contract_path.write_text(
                __import__("yaml").safe_dump(
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
        self.assertIn("report_payload:", stdout_buffer.getvalue())
        self.assertIn("template_id: autoreport-editorial-v1", stdout_buffer.getvalue())

    def test_generate_command_writes_presentation(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "payload.yaml"
            output_path = test_dir / "autoreport_demo.pptx"
            write_payload(payload_path)

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

    def test_generate_command_reports_validation_errors(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "invalid_payload.yaml"
            payload_path.write_text(
                "\n".join(
                    [
                        "report_payload:",
                        "  payload_version: autoreport.payload.v1",
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
        self.assertEqual(
            stderr_buffer.getvalue().splitlines(),
            [
                "Payload validation failed.",
                "- Field 'title_slide.title' must be a non-empty string.",
                "- Field 'title_slide.subtitle' must contain at least 1 item.",
                "- Field 'slides' must contain at least 1 item.",
            ],
        )

    def test_generate_command_reports_missing_template(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            payload_path = test_dir / "payload.yaml"
            write_payload(payload_path)

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        str(payload_path),
                        "--template",
                        str(test_dir / "missing-template.pptx"),
                    ]
                )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("Template file not found:", stderr_buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
