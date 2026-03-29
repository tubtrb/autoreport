"""Branch-local reporting adapter for v0.4 workflow automation rehearsals."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CODEX_DIR_NAME = ".codex"
WORKSTREAM_KEY = "workflow-automation"
WORKSTREAM_TEST_MODULES = (
    "tests.test_workflow_automation_spike",
    "tests.test_workflow_automation_sandbox",
    "tests.test_generator",
)
WORKSTREAM_METADATA = {
    "key": WORKSTREAM_KEY,
    "test_modules": list(WORKSTREAM_TEST_MODULES),
    "orchestration_enabled": True,
}
STATUS_PATH_NAME = "worker-status.json"
FINAL_PATH_NAME = "worker-final.json"


def resolve_repo_root(repo_root: Path | None = None) -> Path:
    return (repo_root or REPO_ROOT).resolve()


def codex_dir(repo_root: Path | None = None) -> Path:
    path = resolve_repo_root(repo_root) / CODEX_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_workstream_metadata(repo_root: Path | None = None) -> Path:
    path = codex_dir(repo_root) / "workstream.json"
    path.write_text(
        json.dumps(WORKSTREAM_METADATA, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def worker_status_path(repo_root: Path | None = None) -> Path:
    return codex_dir(repo_root) / STATUS_PATH_NAME


def worker_final_path(repo_root: Path | None = None) -> Path:
    return codex_dir(repo_root) / FINAL_PATH_NAME


def invalidate_worker_final(repo_root: Path | None = None) -> None:
    path = worker_final_path(repo_root)
    if path.exists():
        path.unlink()


def narrow_test_command(repo_root: Path | None = None) -> str:
    resolved_repo_root = resolve_repo_root(repo_root)
    python_path = resolved_repo_root / ".venv" / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = resolved_repo_root / "venv" / "Scripts" / "python.exe"
    executable = str(python_path) if python_path.exists() else "python"
    return " ".join([executable, "-m", "unittest", *WORKSTREAM_TEST_MODULES])


def sandbox_command(sandbox_root: Path, *, repo_root: Path | None = None) -> str:
    resolved_repo_root = resolve_repo_root(repo_root)
    python_path = resolved_repo_root / ".venv" / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = resolved_repo_root / "venv" / "Scripts" / "python.exe"
    executable = str(python_path) if python_path.exists() else "python"
    return " ".join(
        [
            executable,
            "-m",
            "experiments.v04.prototypes.workflow_automation_sandbox",
            "--sandbox",
            str(sandbox_root.resolve()),
        ]
    )


def sandbox_input_summary(
    *,
    sandbox_root: Path,
    config_path: Path,
    brief_path: Path,
    template_name: str,
    template_path: Path | None,
) -> str:
    template_value = (
        str(template_path.resolve()) if template_path is not None else template_name
    )
    return (
        f"sandbox={sandbox_root.resolve()}; "
        f"config={config_path.resolve()}; "
        f"brief={brief_path.resolve()}; "
        f"template={template_value}"
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def existing_absolute_paths(paths: list[Path]) -> list[str]:
    seen: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        resolved = str(path.resolve())
        if resolved not in seen:
            seen.append(resolved)
    return seen


def _run_git(args: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def current_git_branch(repo_root: Path | None = None) -> str:
    resolved_repo_root = resolve_repo_root(repo_root)
    completed = _run_git(["branch", "--show-current"], resolved_repo_root)
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def current_git_head(repo_root: Path | None = None) -> str:
    resolved_repo_root = resolve_repo_root(repo_root)
    completed = _run_git(["rev-parse", "HEAD"], resolved_repo_root)
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def current_working_tree_clean(repo_root: Path | None = None) -> bool:
    resolved_repo_root = resolve_repo_root(repo_root)
    completed = _run_git(["status", "--porcelain"], resolved_repo_root)
    if completed.returncode != 0:
        return False
    return not bool(completed.stdout.strip())


def sync_notes(repo_root: Path | None = None) -> str:
    notes = (
        "v0.4 workflow automation emits collector-compatible .codex reports only; "
        "it does not participate in v0.3 branch discovery, policy sync, or "
        "retired-directory cleanup."
    )
    if current_git_branch(repo_root) == "unknown":
        notes += " Git metadata was unavailable while writing this local report."
    return notes


def write_worker_status(
    *,
    repo_root: Path | None = None,
    status: str,
    task_summary: str,
    evidence_input: str,
    evidence_command: str,
    artifact_paths: list[Path],
    visible_result: str,
    remaining_gap: str,
) -> Path:
    ensure_workstream_metadata(repo_root)
    invalidate_worker_final(repo_root)
    payload = {
        "workstream_key": WORKSTREAM_KEY,
        "branch": current_git_branch(repo_root),
        "head": current_git_head(repo_root),
        "updated_at": now_iso(),
        "status": status,
        "task_summary": task_summary,
        "last_green_test_command": narrow_test_command(repo_root),
        "working_tree_clean": current_working_tree_clean(repo_root),
        "sync_notes": sync_notes(repo_root),
        "evidence": {
            "input": evidence_input,
            "command": evidence_command,
            "artifact_paths": existing_absolute_paths(artifact_paths),
            "visible_result": visible_result,
            "remaining_gap": remaining_gap,
        },
    }
    path = worker_status_path(repo_root)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_workflow_automation_run(
    *,
    sandbox_root: Path,
    completion_summary: str,
    known_gaps: str,
    repo_root: Path | None = None,
) -> Path:
    if not completion_summary.strip():
        raise ValueError("completion_summary must be a non-empty string.")
    if not known_gaps.strip():
        raise ValueError("known_gaps must be a non-empty string.")

    resolved_repo_root = resolve_repo_root(repo_root)
    ensure_workstream_metadata(resolved_repo_root)

    summary_path = sandbox_root.resolve() / "logs" / "run-summary.json"
    review_path = sandbox_root.resolve() / "reviews" / "review-notes.md"
    if not summary_path.exists():
        raise FileNotFoundError(f"Sandbox summary is missing: {summary_path}")
    if not review_path.exists():
        raise FileNotFoundError(f"Review notes are missing: {review_path}")

    status_path = worker_status_path(resolved_repo_root)
    if not status_path.exists():
        raise FileNotFoundError(
            "worker-status.json is missing. Run the sandbox successfully before finalizing."
        )
    status_payload = _load_json(status_path)
    if status_payload.get("status") == "blocked":
        raise ValueError("Cannot finalize a blocked workflow automation run.")

    summary_payload = _load_json(summary_path)
    artifact_path = Path(summary_payload["artifact_path"]).resolve()
    if not artifact_path.exists():
        raise FileNotFoundError(f"Primary artifact is missing: {artifact_path}")

    artifact_paths = [
        artifact_path,
        review_path,
        summary_path,
    ]
    payload = {
        "workstream_key": WORKSTREAM_KEY,
        "branch": status_payload.get("branch") or current_git_branch(resolved_repo_root),
        "head": status_payload.get("head") or current_git_head(resolved_repo_root),
        "completed_at": now_iso(),
        "completion_summary": completion_summary.strip(),
        "last_green_test_command": status_payload.get("last_green_test_command")
        or narrow_test_command(resolved_repo_root),
        "primary_artifact_path": str(artifact_path),
        "artifact_paths": existing_absolute_paths(artifact_paths),
        "visible_result": (
            f"Approved workflow automation artifact at {artifact_path} with review notes at "
            f"{review_path}."
        ),
        "known_gaps": known_gaps.strip(),
        "ready_for_master_review": True,
    }
    path = worker_final_path(resolved_repo_root)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Finalize a successful v0.4 workflow automation sandbox run for orchestration handoff."
    )
    parser.add_argument(
        "--sandbox",
        required=True,
        help="Absolute or relative path to the sandbox root to finalize.",
    )
    parser.add_argument(
        "--completion-summary",
        required=True,
        help="Short human summary of what is complete.",
    )
    parser.add_argument(
        "--known-gaps",
        required=True,
        help="Known gaps or remaining caveats for the handoff.",
    )
    parser.add_argument(
        "--repo-root",
        help="Optional override for the repo root that should receive .codex artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    final_path = finalize_workflow_automation_run(
        sandbox_root=Path(args.sandbox),
        completion_summary=args.completion_summary,
        known_gaps=args.known_gaps,
        repo_root=(None if args.repo_root is None else Path(args.repo_root)),
    )
    print(
        json.dumps(
            {
                "worker_final_path": str(final_path.resolve()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
