"""Tests for report generation and PowerPoint output."""

from __future__ import annotations

import os
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

    def test_generate_report_from_mapping_creates_weekly_presentation(self) -> None:
        test_dir = make_test_dir()
        try:
            output_path = test_dir / "output" / "weekly_report.pptx"

            generated_path = generate_report_from_mapping(
                {
                    "title": "Weekly Report",
                    "team": "Platform Team",
                    "week": "2026-W24",
                    "highlights": ["Built the generation pipeline."],
                    "metrics": {
                        "tasks_completed": 8,
                        "open_issues": 3,
                    },
                    "risks": ["Layout polish is still pending."],
                    "next_steps": ["Review the generated deck."],
                },
                output_path=output_path,
            )

            presentation = Presentation(str(output_path))
            slide_titles = [slide.shapes.title.text for slide in presentation.slides]
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(generated_path, output_path)
        self.assertEqual(
            slide_titles,
            ["Weekly Report", "Highlights", "Metrics", "Risks", "Next Steps"],
        )

    def test_prepare_generation_artifacts_profiles_default_template(self) -> None:
        artifacts = prepare_generation_artifacts_from_mapping(
            {
                "title": "Weekly Report",
                "team": "Platform Team",
                "week": "2026-W24",
                "highlights": ["Built the generation pipeline."],
                "metrics": {
                    "tasks_completed": 8,
                    "open_issues": 3,
                },
                "risks": ["Layout polish is still pending."],
                "next_steps": ["Review the generated deck."],
            },
            presentation=Presentation(),
        )

        self.assertEqual(artifacts.template_profile.title_layout_index, 0)
        self.assertEqual(artifacts.template_profile.body_layout_index, 1)
        self.assertEqual(artifacts.template_profile.title_slot.placeholder_index, 0)
        self.assertEqual(
            artifacts.template_profile.body_content_slot.placeholder_index,
            1,
        )
        self.assertEqual(len(artifacts.content_blocks), 5)
        self.assertEqual(len(artifacts.fill_plan.slides), 5)
        self.assertEqual(artifacts.diagnostic_report.errors, [])

    def test_prepare_generation_artifacts_spills_long_content_to_continuation_slide(self) -> None:
        long_highlights = [
            "This is a deliberately long highlight item that keeps expanding "
            f"to force spill behavior across multiple slides {index}. "
            * 2
            for index in range(1, 15)
        ]
        artifacts = prepare_generation_artifacts_from_mapping(
            {
                "title": "Weekly Report",
                "team": "Platform Team",
                "week": "2026-W24",
                "highlights": long_highlights,
                "metrics": {
                    "tasks_completed": 8,
                    "open_issues": 3,
                },
                "risks": ["Layout polish is still pending."],
                "next_steps": ["Review the generated deck."],
            },
            presentation=Presentation(),
        )

        slide_titles = [slide.title_text for slide in artifacts.fill_plan.slides]
        warning_codes = [
            entry.code for entry in artifacts.diagnostic_report.warnings
        ]

        self.assertIn("Highlights (cont.)", slide_titles)
        self.assertIn("overflow-spill", warning_codes)

    def test_prepare_generation_artifacts_flags_font_risk_for_user_template(self) -> None:
        artifacts = prepare_generation_artifacts_from_mapping(
            {
                "title": "Weekly Report",
                "team": "Platform Team",
                "week": "2026-W24",
                "highlights": ["Built the generation pipeline."],
                "metrics": {
                    "tasks_completed": 8,
                    "open_issues": 3,
                },
                "risks": ["Layout polish is still pending."],
                "next_steps": ["Review the generated deck."],
            },
            presentation=Presentation(),
            template_path=Path("corporate-template.pptx"),
        )

        warning_codes = [
            entry.code for entry in artifacts.diagnostic_report.warnings
        ]
        self.assertIn("font-substitution-risk", warning_codes)

    def test_prepare_generation_artifacts_warns_when_one_item_exceeds_slot_budget(self) -> None:
        oversized_highlight = "Oversized highlight " * 180
        artifacts = prepare_generation_artifacts_from_mapping(
            {
                "title": "Weekly Report",
                "team": "Platform Team",
                "week": "2026-W24",
                "highlights": [oversized_highlight],
                "metrics": {
                    "tasks_completed": 8,
                    "open_issues": 3,
                },
                "risks": ["Layout polish is still pending."],
                "next_steps": ["Review the generated deck."],
            },
            presentation=Presentation(),
        )

        warning_codes = [
            entry.code for entry in artifacts.diagnostic_report.warnings
        ]
        self.assertIn("out-of-bounds-risk", warning_codes)
