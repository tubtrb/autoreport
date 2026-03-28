"""Template helpers for weekly report slide generation."""

from __future__ import annotations

from typing import Any

from autoreport.models import WeeklyReport


TEMPLATE_NAME = "weekly_report"
METRIC_LABELS = (
    ("tasks_completed", "Tasks completed"),
    ("open_issues", "Open issues"),
)


def build_weekly_report_context(report: WeeklyReport) -> dict[str, Any]:
    """Prepare slide-friendly context for a weekly report presentation."""

    metric_items = [
        f"{label}: {report.metrics[key]}"
        for key, label in METRIC_LABELS
    ]

    return {
        "slides": [
            {
                "layout": "title",
                "title": report.title,
                "subtitle": f"{report.team}\n{report.week}",
            },
            {
                "layout": "bullets",
                "title": "Highlights",
                "items": list(report.highlights),
            },
            {
                "layout": "bullets",
                "title": "Metrics",
                "items": metric_items,
            },
            {
                "layout": "bullets",
                "title": "Risks",
                "items": list(report.risks),
            },
            {
                "layout": "bullets",
                "title": "Next Steps",
                "items": list(report.next_steps),
            },
        ]
    }
