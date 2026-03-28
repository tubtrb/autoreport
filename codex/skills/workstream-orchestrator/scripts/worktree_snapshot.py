from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workstream:
    key: str
    folder: str
    test_modules: tuple[str, ...]


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKSPACE_ROOT = REPO_ROOT.parent
SHARED_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"
WORKSTREAMS = (
    Workstream(
        key="template-contract-export",
        folder="autoreport_v0.3-template-contract-export",
        test_modules=("tests.test_generator", "tests.test_pptx_writer"),
    ),
    Workstream(
        key="generic-payload-schema",
        folder="autoreport_v0.3-generic-payload-schema",
        test_modules=("tests.test_validator", "tests.test_loader"),
    ),
    Workstream(
        key="text-layout-engine",
        folder="autoreport_v0.3-text-layout-engine",
        test_modules=(
            "tests.test_autofill",
            "tests.test_generator",
            "tests.test_pptx_writer",
        ),
    ),
    Workstream(
        key="image-layout-engine",
        folder="autoreport_v0.3-image-layout-engine",
        test_modules=("tests.test_generator", "tests.test_pptx_writer"),
    ),
    Workstream(
        key="cli-web-template-flow",
        folder="autoreport_v0.3-cli-web-template-flow",
        test_modules=("tests.test_cli", "tests.test_web_app"),
    ),
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
    worktree = WORKSPACE_ROOT / workstream.folder
    data: dict[str, object] = {
        "key": workstream.key,
        "path": str(worktree),
        "recommended_test_command": " ".join(
            [str(SHARED_PYTHON), "-m", "unittest", *workstream.test_modules]
        ),
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
        if SHARED_PYTHON.exists():
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
        description="Snapshot autoreport sibling worktrees for master-thread orchestration."
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run the narrow recommended test suite for each known workstream.",
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
        "workstreams": [
            snapshot_workstream(workstream, args.run_tests)
            for workstream in WORKSTREAMS
        ],
    }
    json.dump(snapshot, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
