"""Input loading utilities for report definition files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML report definition from disk as raw parsed data."""

    report_path = Path(path)
    if not report_path.exists() or not report_path.is_file():
        raise FileNotFoundError(report_path)

    with report_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)

    return cast(dict[str, Any], loaded)
