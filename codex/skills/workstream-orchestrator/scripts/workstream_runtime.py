from __future__ import annotations

import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKSPACE_ROOT = REPO_ROOT.parent
SHARED_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"
DEFAULT_BRANCH_PREFIX = "codex/v0.3-"
DEFAULT_EXCLUDE_BRANCHES = {
    "codex/v0.3-master",
}
DEFAULT_EXCLUDE_PATTERNS = (
    "codex/v0.3-bootstrap-*",
    "codex/v0.3-salvage-*",
)
WORKSTREAM_CONFIG_NAME = "workstream.json"


@dataclass(frozen=True)
class Workstream:
    key: str
    branch: str
    path: Path
    test_modules: tuple[str, ...]


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def parse_worktree_list(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        field, _, value = line.partition(" ")
        current[field] = value
    if current:
        entries.append(current)
    return entries


def normalize_branch_name(raw: str) -> str:
    if raw.startswith("refs/heads/"):
        return raw[len("refs/heads/") :]
    return raw


def derive_workstream_key(branch: str, branch_prefix: str) -> str:
    if branch.startswith(branch_prefix):
        return branch[len(branch_prefix) :]
    return branch.replace("/", "-")


def infer_test_modules(key: str) -> tuple[str, ...]:
    modules: list[str] = []
    if "contract" in key or "schema" in key or "payload" in key:
        modules.extend(["tests.test_loader", "tests.test_validator"])
    if "web" in key or "cli" in key:
        modules.extend(["tests.test_cli", "tests.test_web_app"])
    if any(token in key for token in ("generation", "preview", "layout", "template", "image", "text")):
        modules.extend(["tests.test_autofill", "tests.test_generator", "tests.test_pptx_writer"])
    if "release" in key:
        modules.extend(["tests.test_cli", "tests.test_web_app"])

    seen: list[str] = []
    for module in modules:
        if module not in seen:
            seen.append(module)
    return tuple(seen)


def load_local_workstream_config(worktree: Path) -> dict[str, Any]:
    config_path = worktree / ".codex" / WORKSTREAM_CONFIG_NAME
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def branch_is_in_scope(
    branch: str,
    branch_prefix: str,
    exclude_branches: set[str],
    exclude_patterns: tuple[str, ...],
) -> bool:
    if not branch.startswith(branch_prefix):
        return False
    if branch in exclude_branches:
        return False
    return not any(fnmatch.fnmatch(branch, pattern) for pattern in exclude_patterns)


def discover_workstreams(
    *,
    branch_prefix: str = DEFAULT_BRANCH_PREFIX,
    exclude_branches: set[str] | None = None,
    exclude_patterns: tuple[str, ...] | None = None,
) -> list[Workstream]:
    exclude_branch_set = set(DEFAULT_EXCLUDE_BRANCHES)
    if exclude_branches:
        exclude_branch_set.update(exclude_branches)
    exclude_pattern_values = DEFAULT_EXCLUDE_PATTERNS if exclude_patterns is None else exclude_patterns

    completed = run_git(["worktree", "list", "--porcelain"])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Failed to list git worktrees.")

    workstreams: list[Workstream] = []
    for entry in parse_worktree_list(completed.stdout):
        branch_raw = entry.get("branch", "")
        branch = normalize_branch_name(branch_raw)
        if not branch_is_in_scope(branch, branch_prefix, exclude_branch_set, exclude_pattern_values):
            continue

        worktree_path = Path(entry["worktree"])
        config = load_local_workstream_config(worktree_path)
        if config.get("orchestration_enabled") is False:
            continue

        key = str(config.get("key") or derive_workstream_key(branch, branch_prefix))
        configured_modules = config.get("test_modules")
        if isinstance(configured_modules, list) and all(isinstance(item, str) for item in configured_modules):
            test_modules = tuple(configured_modules)
        else:
            test_modules = infer_test_modules(key)
        workstreams.append(
            Workstream(
                key=key,
                branch=branch,
                path=worktree_path,
                test_modules=test_modules,
            )
        )

    return sorted(workstreams, key=lambda item: (item.key, str(item.path)))


def recommended_test_command(workstream: Workstream) -> str:
    if not workstream.test_modules:
        return ""
    return " ".join([str(SHARED_PYTHON), "-m", "unittest", *workstream.test_modules])
