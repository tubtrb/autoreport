#!/usr/bin/env python3
"""Guard direct commits on protected integration branches."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

PROTECTED_BRANCHES = {"codex/next", "codex/master"}


def detect_current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "failed to detect the current branch"
        raise RuntimeError(message)
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("git reported an empty branch name")
    return branch


def slugify(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug or "task"


def suggested_branch_name(branch: str, task: str) -> str:
    return f"{branch}-{slugify(task)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Block routine direct commits on protected integration branches."
    )
    parser.add_argument(
        "--branch",
        help="Branch name to evaluate. Defaults to the current git branch.",
    )
    parser.add_argument(
        "--task",
        default="task",
        help="Short task slug used in the suggested child branch name.",
    )
    parser.add_argument(
        "--allow-protected",
        action="store_true",
        help=(
            "Bypass the block for intentional integration work on a protected "
            "branch, such as merge, squash, sync, release promotion, or another "
            "explicit user-approved exception."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    branch = args.branch or detect_current_branch()
    if branch in PROTECTED_BRANCHES and not args.allow_protected:
        suggestion = suggested_branch_name(branch, args.task)
        print(
            f"[BLOCKED] Direct commits are disabled on protected branch '{branch}'.",
            file=sys.stderr,
        )
        print(
            "Create or switch to a child branch first, for example:",
            file=sys.stderr,
        )
        print(f"  git switch -c {suggestion}", file=sys.stderr)
        print(
            "Use --allow-protected only for intentional integration work on "
            "this branch, such as merge, squash, sync, release promotion, or "
            "another explicit user-approved direct commit.",
            file=sys.stderr,
        )
        return 2

    if branch in PROTECTED_BRANCHES:
        print(
            f"[OVERRIDE] Protected branch '{branch}' allowed for intentional "
            "integration work because --allow-protected was supplied."
        )
        return 0

    print(f"[OK] Branch '{branch}' is allowed for direct commits under current policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
