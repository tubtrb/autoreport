"""Input loading utilities for report definition files."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, cast

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML report definition from disk as raw parsed data."""

    report_path = Path(path)
    if not report_path.exists() or not report_path.is_file():
        raise FileNotFoundError(report_path)

    with report_path.open("r", encoding="utf-8") as handle:
        return parse_yaml_text(handle.read())


def parse_yaml_text(text: str) -> dict[str, Any]:
    """Parse raw YAML text into the unvalidated report mapping."""

    loaded = yaml.safe_load(_extract_yaml_text(text))
    return cast(dict[str, Any], loaded)


def _extract_yaml_text(text: str) -> str:
    """Accept plain YAML or the first fenced code block containing YAML."""

    stripped = text.strip()
    fence_match = re.search(r"```(?:yaml|yml)?[^\n]*\n(.*?)\n```", stripped, re.DOTALL)
    if fence_match is not None:
        prefix = stripped[: fence_match.start()].strip()
        suffix = stripped[fence_match.end() :].strip()
        if _looks_like_yaml_content(prefix) or _looks_like_yaml_content(suffix):
            raise yaml.YAMLError(
                "Mixed fenced and unfenced YAML content is not supported. "
                "Return one complete YAML document, either plain or inside a single fenced code block."
            )
        return fence_match.group(1).strip()
    return stripped


def _looks_like_yaml_content(text: str) -> bool:
    """Return True when surrounding text looks like partial YAML rather than prose."""

    if not text:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^-\s+[A-Za-z0-9_\"'-]+\s*:", stripped):
            return True
        if re.match(r"^[A-Za-z0-9_\"'-]+\s*:", stripped):
            return True
    return False
