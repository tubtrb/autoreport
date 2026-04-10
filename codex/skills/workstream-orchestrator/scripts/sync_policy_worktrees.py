from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workstream_runtime import (
    REPO_ROOT,
    SHARED_PYTHON,
    WORKSPACE_ROOT,
    Workstream,
    discover_workstreams,
    infer_active_base_branch,
    recommended_test_command,
    run_git,
)


def run_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def command_ok(args: list[str], cwd: Path) -> bool:
    return run_command(args, cwd).returncode == 0


def command_output(args: list[str], cwd: Path) -> str:
    completed = run_command(args, cwd)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def worktree_is_dirty(worktree: Path) -> bool:
    completed = run_command(["git", "status", "--porcelain"], worktree)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"Failed to inspect git status in {worktree}")
    return bool(completed.stdout.strip())


def branch_has_remote(branch: str) -> bool:
    completed = run_git(["rev-parse", "--verify", f"refs/remotes/origin/{branch}"])
    return completed.returncode == 0


def branch_unique_commit_count(worktree: Path, base_ref: str, branch: str) -> int:
    completed = run_command(["git", "rev-list", "--count", f"{base_ref}..{branch}"], worktree)
    if completed.returncode != 0:
        return 0
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return 0


def checkpoint_dirty_worktree(workstream: Workstream, message: str, dry_run: bool) -> str | None:
    if dry_run:
        return f"DRY-RUN {message}"
    add_completed = run_command(["git", "add", "-A"], workstream.path)
    if add_completed.returncode != 0:
        raise RuntimeError(add_completed.stderr.strip() or f"Failed to stage changes in {workstream.path}")
    commit_completed = run_command(["git", "commit", "-m", message], workstream.path)
    if commit_completed.returncode != 0:
        raise RuntimeError(commit_completed.stderr.strip() or f"Failed to checkpoint dirty worktree {workstream.key}")
    return command_output(["git", "rev-parse", "HEAD"], workstream.path)


def ensure_on_branch(workstream: Workstream) -> None:
    current_branch = command_output(["git", "branch", "--show-current"], workstream.path)
    if current_branch != workstream.branch:
        raise RuntimeError(
            f"Worktree {workstream.path} is on {current_branch or '<detached>'}, expected {workstream.branch}."
        )


def run_narrow_tests(workstream: Workstream, dry_run: bool) -> dict[str, Any]:
    if not workstream.test_modules:
        return {
            "command": "",
            "ok": None,
            "exit_code": None,
            "stdout": "",
            "stderr": "No narrow test modules configured.",
        }
    command = [str(SHARED_PYTHON), "-m", "unittest", *workstream.test_modules]
    if dry_run:
        return {
            "command": " ".join(command),
            "ok": None,
            "exit_code": None,
            "stdout": "",
            "stderr": "DRY-RUN",
        }
    completed = run_command(command, workstream.path)
    return {
        "command": " ".join(command),
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def push_branch(workstream: Workstream, dry_run: bool) -> dict[str, Any]:
    remote_exists = branch_has_remote(workstream.branch)
    if dry_run:
        return {
            "remote_exists": remote_exists,
            "pushed": True,
            "command": "git push --force-with-lease" if remote_exists else f"git push -u origin {workstream.branch}",
        }
    args = ["git", "push", "--force-with-lease"] if remote_exists else ["git", "push", "-u", "origin", workstream.branch]
    completed = run_command(args, workstream.path)
    return {
        "remote_exists": remote_exists,
        "pushed": completed.returncode == 0,
        "command": " ".join(args),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def sync_workstream(
    workstream: Workstream,
    *,
    base_branch: str,
    checkpoint_dirty: bool,
    push: bool,
    dry_run: bool,
) -> dict[str, Any]:
    ensure_on_branch(workstream)
    base_ref = f"origin/{base_branch}"
    result: dict[str, Any] = {
        "key": workstream.key,
        "branch": workstream.branch,
        "path": str(workstream.path),
        "base_ref": base_ref,
        "recommended_test_command": recommended_test_command(workstream),
        "checkpoint_commit": None,
        "push": None,
        "errors": [],
    }

    dirty = worktree_is_dirty(workstream.path)
    result["dirty_before"] = dirty
    if dirty:
        if not checkpoint_dirty:
            result["errors"].append(
                "Dirty worktree requires --checkpoint-dirty before policy sync can continue."
            )
            return result
        checkpoint_message = (
            f"chore: checkpoint before policy sync ({workstream.key}) "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )
        try:
            result["checkpoint_commit"] = checkpoint_dirty_worktree(workstream, checkpoint_message, dry_run)
        except RuntimeError as exc:
            result["errors"].append(str(exc))
            return result

    unique_before = branch_unique_commit_count(workstream.path, base_ref, workstream.branch)
    result["unique_commits_before"] = unique_before

    if dry_run:
        result["rebase"] = {"ok": True, "command": f"git rebase {base_ref}"}
    else:
        rebase_completed = run_command(["git", "rebase", base_ref], workstream.path)
        result["rebase"] = {
            "ok": rebase_completed.returncode == 0,
            "command": f"git rebase {base_ref}",
            "stdout": rebase_completed.stdout.strip(),
            "stderr": rebase_completed.stderr.strip(),
        }
        if rebase_completed.returncode != 0:
            result["errors"].append(result["rebase"]["stderr"] or "Rebase failed.")
            return result

    test_result = run_narrow_tests(workstream, dry_run)
    result["tests"] = test_result
    if test_result["ok"] is False:
        result["errors"].append(test_result["stderr"] or "Narrow tests failed.")
        return result

    if push:
        should_push = branch_has_remote(workstream.branch) or unique_before > 0
        if should_push:
            push_result = push_branch(workstream, dry_run)
            result["push"] = push_result
            if not push_result["pushed"]:
                result["errors"].append(push_result.get("stderr") or "Push failed.")
        else:
            result["push"] = {
                "remote_exists": False,
                "pushed": False,
                "skipped": True,
                "reason": "No remote branch and no unique commits beyond base.",
            }

    result["ok"] = not result["errors"]
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Checkpoint, rebase, test, and optionally push active task worktrees after a master-owned policy change."
    )
    parser.add_argument(
        "--base-branch",
        default=infer_active_base_branch(),
        help="Shared version-master branch that discovered task worktrees should rebase onto. Defaults to the inferred active version-master branch.",
    )
    parser.add_argument(
        "--checkpoint-dirty",
        action="store_true",
        help="Create a checkpoint commit automatically when a task worktree is dirty.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push updated task branches after a successful rebase and narrow test run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would happen without rebasing, testing, or pushing.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result.",
    )
    return parser.parse_args()


def fetch_base(base_branch: str, dry_run: bool) -> dict[str, Any]:
    command = ["git", "fetch", "origin", base_branch]
    if dry_run:
        return {"ok": True, "command": " ".join(command), "stdout": "", "stderr": "DRY-RUN"}
    completed = run_command(command, REPO_ROOT)
    return {
        "ok": completed.returncode == 0,
        "command": " ".join(command),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    args = parse_args()
    fetch_result = fetch_base(args.base_branch, args.dry_run)
    if not fetch_result["ok"]:
        payload = {"fetch": fetch_result, "workstreams": []}
        json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
        sys.stdout.write("\n")
        return 1

    workstreams = discover_workstreams(base_branch=args.base_branch)
    results = [
        sync_workstream(
            workstream,
            base_branch=args.base_branch,
            checkpoint_dirty=args.checkpoint_dirty,
            push=args.push,
            dry_run=args.dry_run,
        )
        for workstream in workstreams
    ]
    success = all(item.get("ok", False) or not item.get("errors") for item in results)
    payload = {
        "repo_root": str(REPO_ROOT),
        "workspace_root": str(WORKSPACE_ROOT),
        "base_branch": args.base_branch,
        "fetch": fetch_result,
        "dry_run": args.dry_run,
        "pushed": args.push,
        "checkpoint_dirty": args.checkpoint_dirty,
        "summary": {
            "total": len(results),
            "ok": [item["key"] for item in results if item.get("ok")],
            "failed": [item["key"] for item in results if item.get("errors")],
            "push_skipped": [
                item["key"]
                for item in results
                if isinstance(item.get("push"), dict) and item["push"].get("skipped")
            ],
        },
        "workstreams": results,
    }
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
