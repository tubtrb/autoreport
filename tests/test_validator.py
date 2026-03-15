"""Tests for strict weekly report schema validation."""

from __future__ import annotations

import unittest

from autoreport.models import WeeklyReport
from autoreport.validator import ValidationError, validate_report


class ValidatorTestCase(unittest.TestCase):
    """Verify weekly report validation rules and model conversion."""

    def test_validate_report_returns_trimmed_weekly_report(self) -> None:
        report = validate_report(
            {
                "title": " Weekly Report ",
                "team": " Platform Team ",
                "week": " 2026-W24 ",
                "highlights": [" Built validator "],
                "metrics": {
                    "tasks_completed": 8,
                    "open_issues": 3,
                },
                "risks": [" Schema drift "],
                "next_steps": [" Add PowerPoint generation "],
            }
        )

        self.assertIsInstance(report, WeeklyReport)
        self.assertEqual(report.title, "Weekly Report")
        self.assertEqual(report.team, "Platform Team")
        self.assertEqual(report.week, "2026-W24")
        self.assertEqual(report.highlights, ["Built validator"])
        self.assertEqual(report.metrics, {"tasks_completed": 8, "open_issues": 3})
        self.assertEqual(report.risks, ["Schema drift"])
        self.assertEqual(report.next_steps, ["Add PowerPoint generation"])

    def test_validate_report_rejects_non_mapping_payload(self) -> None:
        with self.assertRaises(ValidationError) as context:
            validate_report(["not", "a", "mapping"])  # type: ignore[arg-type]

        self.assertEqual(
            context.exception.errors,
            ["Report content must be a YAML mapping."],
        )

    def test_validate_report_collects_errors_in_expected_order(self) -> None:
        with self.assertRaises(ValidationError) as context:
            validate_report(
                {
                    "title": "   ",
                    "week": 202624,
                    "highlights": ["valid", "   ", 12],
                    "metrics": {
                        "tasks_completed": True,
                        "open_issues": -1,
                        "extra_metric": 99,
                    },
                    "risks": [],
                    "next_steps": "ship it",
                    "report_type": "weekly_report",
                    "unexpected": "value",
                }
            )

        self.assertEqual(
            context.exception.errors,
            [
                "Field 'title' must be a non-empty string.",
                "Field 'team' is required.",
                "Field 'week' must be a non-empty string.",
                "Field 'highlights[1]' must be a non-empty string.",
                "Field 'highlights[2]' must be a non-empty string.",
                "Field 'metrics.tasks_completed' must be an integer.",
                "Field 'metrics.open_issues' must be greater than or equal to 0.",
                "Field 'metrics.extra_metric' is not allowed.",
                "Field 'risks' must contain at least 1 item.",
                "Field 'next_steps' must be a list of non-empty strings.",
                "Field 'report_type' is not supported in v0.1.",
                "Field 'unexpected' is not allowed.",
            ],
        )

    def test_validate_report_rejects_missing_required_metrics(self) -> None:
        with self.assertRaises(ValidationError) as context:
            validate_report(
                {
                    "title": "Weekly Report",
                    "team": "Platform Team",
                    "week": "2026-W24",
                    "highlights": ["Highlight"],
                    "metrics": {},
                    "risks": ["Risk"],
                    "next_steps": ["Next step"],
                }
            )

        self.assertEqual(
            context.exception.errors,
            [
                "Field 'metrics.tasks_completed' is required.",
                "Field 'metrics.open_issues' is required.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
