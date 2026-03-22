"""Tests for CLI validation behavior."""

from __future__ import annotations

import io
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from autoreport.cli import main
from autoreport.outputs.pptx_writer import (
    OutputWriteError,
    TemplateCompatibilityError,
    TemplateReadError,
)


TEST_TEMP_ROOT = Path("tests") / "_tmp"


def make_test_dir() -> Path:
    """Create a writable test directory inside the repository."""

    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


class CLITestCase(unittest.TestCase):
    """Verify the CLI generates outputs and reports failures cleanly."""

    def test_generate_command_writes_presentation(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            output_path = test_dir / "weekly_report.pptx"

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        "examples/weekly_report.yaml",
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
            [f"Report generated successfully: {output_path}"],
        )
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertTrue(output_exists)

    def test_generate_command_reports_missing_file(self) -> None:
        missing_path = "examples/missing.yaml"
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(["generate", missing_path])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().strip(),
            f"Report file not found: {missing_path}",
        )

    def test_generate_command_reports_validation_errors(self) -> None:
        invalid_yaml = """title: "  "
team: Platform Team
week: 2026-W11
highlights: []
metrics:
  tasks_completed: -1
  extra_metric: 5
risks:
  - Risk item
next_steps:
  - Next step
"""
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        test_dir = make_test_dir()
        try:
            report_path = test_dir / "invalid_report.yaml"
            report_path.write_text(invalid_yaml, encoding="utf-8")

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["generate", str(report_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().splitlines(),
            [
                "Report validation failed.",
                "- Field 'title' must be a non-empty string.",
                "- Field 'highlights' must contain at least 1 item.",
                "- Field 'metrics.tasks_completed' must be greater than or equal to 0.",
                "- Field 'metrics.open_issues' is required.",
                "- Field 'metrics.extra_metric' is not allowed.",
            ],
        )

    def test_generate_command_reports_yaml_parse_errors(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        test_dir = make_test_dir()
        try:
            report_path = test_dir / "broken.yaml"
            report_path.write_text("title: [broken", encoding="utf-8")

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["generate", str(report_path)])
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("Failed to parse YAML:", stderr_buffer.getvalue())

    def test_generate_command_reports_output_write_errors(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        output_path = Path("output") / "weekly_report.pptx"

        with patch(
            "autoreport.cli.generate_report",
            side_effect=OutputWriteError(output_path),
        ):
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["generate", "examples/weekly_report.yaml"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().strip(),
            f"Could not write report file: {output_path}",
        )

    def test_generate_command_reports_missing_template(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        template_path = "tests/missing-template.pptx"

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(
                [
                    "generate",
                    "examples/weekly_report.yaml",
                    "--template",
                    template_path,
                ]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().strip(),
            f"Template file not found: {Path(template_path)}",
        )

    def test_generate_command_reports_invalid_template(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        test_dir = make_test_dir()
        try:
            template_path = test_dir / "invalid-template.pptx"
            template_path.write_text("not a pptx", encoding="utf-8")

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(
                    [
                        "generate",
                        "examples/weekly_report.yaml",
                        "--template",
                        str(template_path),
                    ]
                )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().strip(),
            f"Invalid PowerPoint template file: {template_path}",
        )

    def test_generate_command_reports_incompatible_template(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        template_path = Path("tests") / "template.pptx"

        with patch(
            "autoreport.cli.generate_report",
            side_effect=TemplateCompatibilityError(
                template_path,
                "missing 'bullets' slide layout at index 1",
            ),
        ):
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["generate", "examples/weekly_report.yaml"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().strip(),
            "PowerPoint template is not compatible with the weekly report layout: "
            "tests\\template.pptx (missing 'bullets' slide layout at index 1)",
        )

    def test_generate_command_reports_template_read_errors(self) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        template_path = Path("tests") / "template.pptx"

        with patch(
            "autoreport.cli.generate_report",
            side_effect=TemplateReadError(template_path),
        ):
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = main(["generate", "examples/weekly_report.yaml"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertEqual(
            stderr_buffer.getvalue().strip(),
            f"Could not read template file: {template_path}",
        )


if __name__ == "__main__":
    unittest.main()
