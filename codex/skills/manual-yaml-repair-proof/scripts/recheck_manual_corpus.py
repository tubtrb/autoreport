from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from autoreport.web.app import (  # noqa: E402
    MANUAL_PUBLIC_TEMPLATE_NAME,
    _append_manual_auto_repair_feedback,
    _build_manual_draft_check,
    _parse_public_payload_yaml,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay saved manual YAML corpus artifacts through the current "
            "auto-repair and manual checker path."
        )
    )
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Artifact directory containing per-sample folders with yaml-candidate.yaml.",
    )
    parser.add_argument(
        "--built-in",
        default=MANUAL_PUBLIC_TEMPLATE_NAME,
        help="Built-in template name for the manual checker.",
    )
    return parser.parse_args()


def classify_payload(payload: dict[str, Any]) -> str:
    if payload.get("ok") and not payload.get("errors"):
        return "manual-pass"
    if payload.get("errors"):
        return "manual-fail"
    return "unknown"


def main() -> int:
    args = parse_args()
    artifact_dir = Path(args.artifact_dir).resolve()
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        raise SystemExit(f"Artifact directory does not exist: {artifact_dir}")

    sample_dirs = sorted(
        path for path in artifact_dir.iterdir() if path.is_dir() and (path / "yaml-candidate.yaml").exists()
    )
    if not sample_dirs:
        raise SystemExit(
            f"No sample folders with yaml-candidate.yaml were found under: {artifact_dir}"
        )

    counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for sample_dir in sample_dirs:
        candidate_text = (sample_dir / "yaml-candidate.yaml").read_text(encoding="utf-8")
        repaired_payload_yaml: str | None = None
        try:
            raw_data, repaired_payload_yaml = _parse_public_payload_yaml(
                candidate_text,
                built_in=args.built_in,
            )
            payload = _build_manual_draft_check(raw_data, built_in=args.built_in)
            if repaired_payload_yaml is not None:
                payload = _append_manual_auto_repair_feedback(
                    payload,
                    repaired_payload_yaml=repaired_payload_yaml,
                )
            category = classify_payload(payload)
        except yaml.YAMLError as exc:
            category = "yaml-parse-failure"
            payload = {
                "ok": False,
                "message": f"Failed to parse YAML: {exc}",
                "errors": [],
                "warnings": [],
                "hints": [],
                "summary": {},
            }

        counts[category] += 1
        rows.append(
            {
                "sample_dir": str(sample_dir),
                "category": category,
                "repaired": repaired_payload_yaml is not None,
                "message": payload.get("message", ""),
                "errors": payload.get("errors", []),
                "warnings": payload.get("warnings", []),
                "summary": payload.get("summary", {}),
            }
        )

    summary_payload = {
        "artifact_dir": str(artifact_dir),
        "sample_count": len(rows),
        "category_counts": dict(sorted(counts.items())),
        "results": rows,
    }
    summary_json_path = artifact_dir / "recheck-summary.json"
    summary_txt_path = artifact_dir / "recheck-summary.txt"
    summary_json_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "Manual YAML Recheck Summary",
        f"Artifact directory: {artifact_dir}",
        f"Collected samples: {len(rows)}",
        "",
        "Category counts:",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("Per-sample results:")
    for index, row in enumerate(rows, start=1):
        repaired_flag = " repaired" if row["repaired"] else ""
        message = row["message"] or ""
        lines.append(
            f"- #{index:03d} {Path(row['sample_dir']).name}: {row['category']}{repaired_flag} | {message}"
        )
    summary_txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(summary_txt_path)
    print(json.dumps({"artifact_dir": str(artifact_dir), "category_counts": dict(counts)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
