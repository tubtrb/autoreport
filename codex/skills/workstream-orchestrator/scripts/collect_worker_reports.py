from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Workstream:
    key: str
    folder: str


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKSPACE_ROOT = REPO_ROOT.parent
WORKSTREAMS = (
    Workstream("template-contract-export", "autoreport_v0.3-template-contract-export"),
    Workstream("generic-payload-schema", "autoreport_v0.3-generic-payload-schema"),
    Workstream("text-layout-engine", "autoreport_v0.3-text-layout-engine"),
    Workstream("image-layout-engine", "autoreport_v0.3-image-layout-engine"),
    Workstream("cli-web-template-flow", "autoreport_v0.3-cli-web-template-flow"),
)

STATUS_VALUES = {"in_progress", "blocked", "ready_for_review"}
STATUS_REQUIRED_FIELDS = {
    "workstream_key": str,
    "branch": str,
    "head": str,
    "updated_at": str,
    "status": str,
    "task_summary": str,
    "last_green_test_command": str,
    "working_tree_clean": bool,
    "sync_notes": str,
}
FINAL_REQUIRED_FIELDS = {
    "workstream_key": str,
    "branch": str,
    "head": str,
    "completed_at": str,
    "completion_summary": str,
    "last_green_test_command": str,
    "primary_artifact_path": str,
    "visible_result": str,
    "known_gaps": str,
    "ready_for_master_review": bool,
}
STATUS_EVIDENCE_REQUIRED_FIELDS = {
    "input": str,
    "command": str,
    "artifact_paths": list,
    "visible_result": str,
    "remaining_gap": str,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect worker checkpoint/final reports from sibling autoreport worktrees."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output.",
    )
    parser.add_argument(
        "--stale-hours",
        type=float,
        default=12.0,
        help="Flag worker-status.json as stale when updated_at is older than this many hours. Default: 12.",
    )
    return parser.parse_args()


def parse_timestamp(raw: str) -> datetime | None:
    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def is_absolute_path(raw: str) -> bool:
    return Path(raw).is_absolute()


def validate_artifact_paths(
    artifact_paths: Any,
    field_name: str,
) -> tuple[list[str], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    normalized_paths: list[str] = []

    if not isinstance(artifact_paths, list):
        errors.append({"field": field_name, "message": "Expected a list of artifact paths."})
        return normalized_paths, errors

    for index, item in enumerate(artifact_paths):
        field = f"{field_name}[{index}]"
        if not isinstance(item, str) or not item.strip():
            errors.append({"field": field, "message": "Expected a non-empty string path."})
            continue
        if not is_absolute_path(item):
            errors.append({"field": field, "message": "Artifact path must be absolute."})
            continue
        normalized_paths.append(item)
        if not Path(item).exists():
            errors.append({"field": field, "message": "Artifact path does not exist."})

    return normalized_paths, errors


def validate_mapping_fields(
    payload: Any,
    required_fields: dict[str, type],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        errors.append({"field": "$", "message": "Expected a JSON object."})
        return errors

    for field, expected_type in required_fields.items():
        if field not in payload:
            errors.append({"field": field, "message": "Missing required field."})
            continue
        value = payload[field]
        if expected_type is bool:
            if not isinstance(value, bool):
                errors.append({"field": field, "message": "Expected a boolean."})
        elif expected_type is list:
            if not isinstance(value, list):
                errors.append({"field": field, "message": "Expected a list."})
        elif not isinstance(value, expected_type):
            errors.append({"field": field, "message": f"Expected {expected_type.__name__}."})
    return errors


def load_json_report(path: Path) -> tuple[Any | None, list[dict[str, str]]]:
    if not path.exists():
        return None, []
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except json.JSONDecodeError as exc:
        return None, [{"field": "$", "message": f"Invalid JSON: {exc.msg}"}]


def collect_status_report(path: Path, stale_after: timedelta) -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": str(path),
        "present": path.exists(),
        "errors": [],
        "artifact_paths": [],
        "status_stale": False,
    }
    payload, parse_errors = load_json_report(path)
    if parse_errors:
        report["errors"] = parse_errors
        return report
    if payload is None:
        return report

    errors = validate_mapping_fields(payload, STATUS_REQUIRED_FIELDS)
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        errors.append({"field": "evidence", "message": "Missing required object."})
        evidence = {}
    else:
        errors.extend(
            {"field": f"evidence.{item['field']}", "message": item["message"]}
            for item in validate_mapping_fields(evidence, STATUS_EVIDENCE_REQUIRED_FIELDS)
        )

    artifact_paths, artifact_errors = validate_artifact_paths(
        evidence.get("artifact_paths", []), "evidence.artifact_paths"
    )
    errors.extend(artifact_errors)

    updated_at_raw = payload.get("updated_at")
    if isinstance(updated_at_raw, str):
        updated_at = parse_timestamp(updated_at_raw)
        if updated_at is None:
            errors.append({"field": "updated_at", "message": "Invalid ISO timestamp."})
        else:
            if updated_at.tzinfo is None:
                errors.append({"field": "updated_at", "message": "Timestamp must include timezone information."})
            else:
                now = datetime.now(updated_at.tzinfo)
                report["status_stale"] = updated_at < now - stale_after

    status_value = payload.get("status")
    if isinstance(status_value, str) and status_value not in STATUS_VALUES:
        errors.append({"field": "status", "message": f"Unsupported value: {status_value}"})

    report.update(
        {
            "workstream_key": payload.get("workstream_key", ""),
            "branch": payload.get("branch", ""),
            "head": payload.get("head", ""),
            "updated_at": payload.get("updated_at", ""),
            "status": payload.get("status", ""),
            "task_summary": payload.get("task_summary", ""),
            "last_green_test_command": payload.get("last_green_test_command", ""),
            "working_tree_clean": payload.get("working_tree_clean"),
            "sync_notes": payload.get("sync_notes", ""),
            "artifact_paths": artifact_paths,
            "errors": errors,
        }
    )
    return report


def collect_final_report(path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": str(path),
        "present": path.exists(),
        "errors": [],
        "artifact_paths": [],
        "primary_artifact_exists": False,
        "ready_for_review": False,
    }
    payload, parse_errors = load_json_report(path)
    if parse_errors:
        report["errors"] = parse_errors
        return report
    if payload is None:
        return report

    errors = validate_mapping_fields(payload, FINAL_REQUIRED_FIELDS)
    artifact_paths, artifact_errors = validate_artifact_paths(
        payload.get("artifact_paths", []), "artifact_paths"
    )
    errors.extend(artifact_errors)

    primary_artifact_path = payload.get("primary_artifact_path", "")
    if isinstance(primary_artifact_path, str) and primary_artifact_path:
        if not is_absolute_path(primary_artifact_path):
            errors.append(
                {"field": "primary_artifact_path", "message": "Primary artifact path must be absolute."}
            )
        else:
            report["primary_artifact_exists"] = Path(primary_artifact_path).exists()
            if not report["primary_artifact_exists"]:
                errors.append(
                    {"field": "primary_artifact_path", "message": "Primary artifact path does not exist."}
                )
    ready = payload.get("ready_for_master_review")
    if ready is not True:
        errors.append(
            {"field": "ready_for_master_review", "message": "Must be true for a final report."}
        )

    completed_at_raw = payload.get("completed_at")
    if isinstance(completed_at_raw, str):
        completed_at = parse_timestamp(completed_at_raw)
        if completed_at is None:
            errors.append({"field": "completed_at", "message": "Invalid ISO timestamp."})
        elif completed_at.tzinfo is None:
            errors.append(
                {"field": "completed_at", "message": "Timestamp must include timezone information."}
            )

    if isinstance(primary_artifact_path, str) and primary_artifact_path and artifact_paths:
        if primary_artifact_path not in artifact_paths:
            errors.append(
                {
                    "field": "artifact_paths",
                    "message": "artifact_paths should include primary_artifact_path for easier review.",
                }
            )

    report.update(
        {
            "workstream_key": payload.get("workstream_key", ""),
            "branch": payload.get("branch", ""),
            "head": payload.get("head", ""),
            "completed_at": payload.get("completed_at", ""),
            "completion_summary": payload.get("completion_summary", ""),
            "last_green_test_command": payload.get("last_green_test_command", ""),
            "primary_artifact_path": primary_artifact_path,
            "artifact_paths": artifact_paths,
            "visible_result": payload.get("visible_result", ""),
            "known_gaps": payload.get("known_gaps", ""),
            "ready_for_review": ready is True and not errors and report["primary_artifact_exists"],
            "errors": errors,
        }
    )
    return report


def collect_workstream(workstream: Workstream, stale_after: timedelta) -> dict[str, Any]:
    worktree = WORKSPACE_ROOT / workstream.folder
    data: dict[str, Any] = {
        "key": workstream.key,
        "path": str(worktree),
        "exists": worktree.exists(),
        "report_missing": True,
        "status_stale": False,
        "ready_for_review": False,
        "final_present": False,
    }
    if not worktree.exists():
        return data

    codex_dir = worktree / ".codex"
    status_report = collect_status_report(codex_dir / "worker-status.json", stale_after)
    final_report = collect_final_report(codex_dir / "worker-final.json")

    report_missing = not status_report["present"] and not final_report["present"]
    final_present = bool(final_report["present"])
    ready_for_review = bool(final_report["ready_for_review"])
    status_stale = bool(status_report["status_stale"])

    data.update(
        {
            "status_report": status_report,
            "final_report": final_report,
            "report_missing": report_missing,
            "status_stale": status_stale,
            "ready_for_review": ready_for_review,
            "final_present": final_present,
        }
    )
    return data


def main() -> int:
    args = parse_args()
    stale_after = timedelta(hours=args.stale_hours)
    workstreams = [collect_workstream(workstream, stale_after) for workstream in WORKSTREAMS]
    summary = {
        "total": len(workstreams),
        "report_missing": [item["key"] for item in workstreams if item["report_missing"]],
        "status_stale": [item["key"] for item in workstreams if item["status_stale"]],
        "ready_for_review": [item["key"] for item in workstreams if item["ready_for_review"]],
        "final_present": [item["key"] for item in workstreams if item["final_present"]],
    }
    payload = {
        "repo_root": str(REPO_ROOT),
        "workspace_root": str(WORKSPACE_ROOT),
        "stale_after_hours": args.stale_hours,
        "summary": summary,
        "workstreams": workstreams,
    }
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
