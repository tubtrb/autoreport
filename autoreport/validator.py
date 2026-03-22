"""Validation helpers for strict weekly report schemas."""

from __future__ import annotations

from typing import Any

from autoreport.models import WeeklyReport


REQUIRED_KEYS = (
    "title",
    "team",
    "week",
    "highlights",
    "metrics",
    "risks",
    "next_steps",
)
METRIC_KEYS = ("tasks_completed", "open_issues")


class ValidationError(Exception):
    """Raised when report data fails schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_report(data: dict[str, Any]) -> WeeklyReport:
    """Validate raw report data and return a typed weekly report model."""

    if not isinstance(data, dict):
        raise ValidationError(["Report content must be a YAML mapping."])

    errors: list[str] = []

    title = _validate_string_field(data, "title", errors)
    team = _validate_string_field(data, "team", errors)
    week = _validate_string_field(data, "week", errors)
    highlights = _validate_string_list_field(data, "highlights", errors)
    metrics = _validate_metrics_field(data, errors)
    risks = _validate_string_list_field(data, "risks", errors)
    next_steps = _validate_string_list_field(data, "next_steps", errors)

    if "report_type" in data:
        errors.append("Field 'report_type' is not supported in v0.1.")

    for key in data:
        if key == "report_type":
            continue
        if key not in REQUIRED_KEYS:
            errors.append(f"Field '{key}' is not allowed.")

    if errors:
        raise ValidationError(errors)

    return WeeklyReport(
        title=title,
        team=team,
        week=week,
        highlights=highlights,
        metrics=metrics,
        risks=risks,
        next_steps=next_steps,
    )


def _validate_string_field(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> str:
    """Validate a required non-empty string field."""

    if field_name not in data:
        errors.append(f"Field '{field_name}' is required.")
        return ""

    value = data[field_name]
    if not isinstance(value, str):
        errors.append(f"Field '{field_name}' must be a non-empty string.")
        return ""

    normalized = value.strip()
    if not normalized:
        errors.append(f"Field '{field_name}' must be a non-empty string.")
        return ""

    return normalized


def _validate_string_list_field(
    data: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> list[str]:
    """Validate a required list of non-empty strings."""

    if field_name not in data:
        errors.append(f"Field '{field_name}' is required.")
        return []

    value = data[field_name]
    if not isinstance(value, list):
        errors.append(
            f"Field '{field_name}' must be a list of non-empty strings."
        )
        return []

    if not value:
        errors.append(f"Field '{field_name}' must contain at least 1 item.")
        return []

    normalized_items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"Field '{field_name}[{index}]' must be a non-empty string."
            )
            continue

        normalized = item.strip()
        if not normalized:
            errors.append(
                f"Field '{field_name}[{index}]' must be a non-empty string."
            )
            continue

        normalized_items.append(normalized)

    return normalized_items


def _validate_metrics_field(
    data: dict[str, Any],
    errors: list[str],
) -> dict[str, int]:
    """Validate the strict metrics object for weekly reports."""

    if "metrics" not in data:
        errors.append("Field 'metrics' is required.")
        return {}

    value = data["metrics"]
    if not isinstance(value, dict):
        errors.append("Field 'metrics' must be an object.")
        return {}

    normalized_metrics: dict[str, int] = {}
    for key in METRIC_KEYS:
        if key not in value:
            errors.append(f"Field 'metrics.{key}' is required.")
            continue

        metric_value = value[key]
        if isinstance(metric_value, bool) or not isinstance(metric_value, int):
            errors.append(f"Field 'metrics.{key}' must be an integer.")
            continue

        if metric_value < 0:
            errors.append(
                f"Field 'metrics.{key}' must be greater than or equal to 0."
            )
            continue

        normalized_metrics[key] = metric_value

    for key in value:
        if key not in METRIC_KEYS:
            errors.append(f"Field 'metrics.{key}' is not allowed.")

    return normalized_metrics
