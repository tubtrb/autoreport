"""Tests for report generation and PowerPoint output."""

from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from pptx import Presentation

from autoreport.engine.generator import generate_report
from autoreport.models import ReportRequest


TEST_TEMP_ROOT = Path("tests") / "_tmp"


def make_test_dir() -> Path:
    """Create a writable test directory inside the repository."""

    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


class GeneratorTestCase(unittest.TestCase):
    """Verify report generation creates the expected PowerPoint structure."""

    def test_generate_report_creates_weekly_presentation(self) -> None:
        test_dir = make_test_dir()
        try:
            report_path = test_dir / "report.yaml"
            output_path = test_dir / "output" / "weekly_report.pptx"
            report_path.write_text(
                "\n".join(
                    [
                        "title: Weekly Report",
                        "team: Platform Team",
                        "week: 2026-W24",
                        "highlights:",
                        "  - Built the generation pipeline.",
                        "metrics:",
                        "  tasks_completed: 8",
                        "  open_issues: 3",
                        "risks:",
                        "  - Layout polish is still pending.",
                        "next_steps:",
                        "  - Review the generated deck.",
                    ]
                ),
                encoding="utf-8",
            )

            generated_path = generate_report(
                ReportRequest(
                    source_path=report_path,
                    output_path=output_path,
                )
            )

            presentation = Presentation(str(output_path))
            slide_titles = [slide.shapes.title.text for slide in presentation.slides]
            title_subtitle = presentation.slides[0].placeholders[1].text
            metrics_text = presentation.slides[2].placeholders[1].text
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(generated_path, output_path)
        self.assertEqual(len(slide_titles), 5)
        self.assertEqual(
            slide_titles,
            ["Weekly Report", "Highlights", "Metrics", "Risks", "Next Steps"],
        )
        self.assertEqual(title_subtitle, "Platform Team\n2026-W24")
        self.assertIn("Tasks completed: 8", metrics_text)
        self.assertIn("Open issues: 3", metrics_text)

    def test_generate_report_uses_default_output_directory(self) -> None:
        test_dir = make_test_dir()
        previous_cwd = Path.cwd()
        try:
            report_path = (test_dir / "weekly_report.yaml").resolve()
            expected_output_path = (test_dir / "output" / "weekly_report.pptx").resolve()
            report_path.write_text(
                "\n".join(
                    [
                        "title: Weekly Report",
                        "team: Platform Team",
                        "week: 2026-W24",
                        "highlights:",
                        "  - Built the generation pipeline.",
                        "metrics:",
                        "  tasks_completed: 8",
                        "  open_issues: 3",
                        "risks:",
                        "  - Layout polish is still pending.",
                        "next_steps:",
                        "  - Review the generated deck.",
                    ]
                ),
                encoding="utf-8",
            )

            os.chdir(test_dir)
            generated_path = generate_report(
                ReportRequest(source_path=report_path)
            )
            generated_exists = expected_output_path.exists()
        finally:
            os.chdir(previous_cwd)
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(generated_path, Path("output") / "weekly_report.pptx")
        self.assertTrue(generated_exists)

    def test_generate_report_replaces_seed_slides_from_template(self) -> None:
        test_dir = make_test_dir()
        try:
            report_path = test_dir / "report.yaml"
            template_path = test_dir / "template.pptx"
            output_path = test_dir / "weekly_report.pptx"

            report_path.write_text(
                "\n".join(
                    [
                        "title: Weekly Report",
                        "team: Platform Team",
                        "week: 2026-W24",
                        "highlights:",
                        "  - Built the generation pipeline.",
                        "metrics:",
                        "  tasks_completed: 8",
                        "  open_issues: 3",
                        "risks:",
                        "  - Layout polish is still pending.",
                        "next_steps:",
                        "  - Review the generated deck.",
                    ]
                ),
                encoding="utf-8",
            )

            template = Presentation()
            template_slide = template.slides.add_slide(template.slide_layouts[0])
            template_slide.shapes.title.text = "Template Seed"
            template_slide.placeholders[1].text = "Keep?"
            template.save(str(template_path))

            generate_report(
                ReportRequest(
                    source_path=report_path,
                    output_path=output_path,
                    template_path=template_path,
                )
            )

            presentation = Presentation(str(output_path))
            slide_titles = [slide.shapes.title.text for slide in presentation.slides]
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(
            slide_titles,
            ["Weekly Report", "Highlights", "Metrics", "Risks", "Next Steps"],
        )
