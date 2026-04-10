from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from workstream_runtime import (
    REPO_ROOT,
    SHARED_PYTHON,
    WORKSPACE_ROOT,
    Workstream,
    discover_workstreams,
    infer_active_base_branch,
    recommended_test_command,
)


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.returncode, completed.stdout, completed.stderr


def command_output(args: list[str], cwd: Path) -> str:
    code, stdout, _stderr = run_command(args, cwd)
    if code != 0:
        return ""
    return stdout.strip()


def snapshot_workstream(workstream: Workstream, run_tests: bool) -> dict[str, object]:
    worktree = workstream.path
    data: dict[str, object] = {
        "key": workstream.key,
        "branch": workstream.branch,
        "path": str(worktree),
        "recommended_test_command": recommended_test_command(workstream),
    }
    if not worktree.exists():
        data["exists"] = False
        return data

    data["exists"] = True
    status_output = command_output(["git", "status", "--short", "--branch"], worktree)
    status_lines = status_output.splitlines() if status_output else []
    changed_output = command_output(["git", "diff", "--name-only", "HEAD"], worktree)
    last_commit_output = command_output(
        ["git", "log", "-1", "--date=iso", "--pretty=format:%H%n%ad%n%s"],
        worktree,
    )
    last_commit_lines = last_commit_output.splitlines() if last_commit_output else []

    data["branch"] = command_output(["git", "branch", "--show-current"], worktree)
    data["status"] = status_lines
    data["clean"] = len(status_lines) <= 1
    data["changed_files"] = changed_output.splitlines() if changed_output else []
    data["last_commit"] = {
        "hash": last_commit_lines[0] if len(last_commit_lines) > 0 else "",
        "date": last_commit_lines[1] if len(last_commit_lines) > 1 else "",
        "subject": last_commit_lines[2] if len(last_commit_lines) > 2 else "",
    }

    if run_tests:
        test_data: dict[str, object] = {
            "modules": list(workstream.test_modules),
            "python": str(SHARED_PYTHON),
        }
        if not workstream.test_modules:
            test_data["exit_code"] = None
            test_data["ok"] = None
            test_data["stdout"] = ""
            test_data["stderr"] = "No narrow test modules configured for this workstream."
        elif SHARED_PYTHON.exists():
            args = [str(SHARED_PYTHON), "-m", "unittest", *workstream.test_modules]
            code, stdout, stderr = run_command(args, worktree)
            test_data["exit_code"] = code
            test_data["ok"] = code == 0
            test_data["stdout"] = stdout.strip()
            test_data["stderr"] = stderr.strip()
        else:
            test_data["exit_code"] = None
            test_data["ok"] = False
            test_data["stdout"] = ""
            test_data["stderr"] = f"Missing shared interpreter: {SHARED_PYTHON}"
        data["tests"] = test_data

    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Snapshot discovered versioned autoreport task worktrees for master-thread orchestration."
    )
    parser.add_argument(
        "--base-branch",
        default=infer_active_base_branch(),
        help="Version-master branch whose child workstreams should be discovered. Defaults to the inferred active version-master branch.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run the narrow recommended test suite for each discovered workstream.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = {
        "repo_root": str(REPO_ROOT),
        "workspace_root": str(WORKSPACE_ROOT),
        "base_branch": args.base_branch,
        "workstreams": [
            snapshot_workstream(workstream, args.run_tests)
            for workstream in discover_workstreams(base_branch=args.base_branch)
        ],
    }
    json.dump(snapshot, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
