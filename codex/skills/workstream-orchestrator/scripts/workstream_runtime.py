from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKSPACE_ROOT = REPO_ROOT.parent
SHARED_PYTHON = REPO_ROOT / "venv" / "Scripts" / "python.exe"
VERSION_MASTER_BRANCH_RE = re.compile(r"^codex/(?P<version>v\d+(?:\.\d+)*)-master$")
PYPROJECT_VERSION_RE = re.compile(r'^\s*version\s*=\s*"(?P<version>[^"]+)"\s*$', re.MULTILINE)
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
    if raw.startswith("refs/remotes/origin/"):
        return raw[len("refs/remotes/origin/") :]
    if raw.startswith("origin/"):
        return raw[len("origin/") :]
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


def read_package_version() -> str:
    pyproject_path = REPO_ROOT / "pyproject.toml"
    try:
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return "0.0.0"
    match = PYPROJECT_VERSION_RE.search(pyproject_text)
    if match is None:
        return "0.0.0"
    return match.group("version")


def version_tuple(version_label: str) -> tuple[int, ...]:
    parts: list[int] = []
    for raw_part in version_label.removeprefix("v").split("."):
        if not raw_part.isdigit():
            return ()
        parts.append(int(raw_part))
    return tuple(parts)


def version_label_from_base_branch(base_branch: str) -> str:
    match = VERSION_MASTER_BRANCH_RE.fullmatch(base_branch)
    if match is not None:
        return match.group("version")
    if base_branch.endswith("-master"):
        branch_without_prefix = base_branch.rsplit("/", 1)[-1]
        return branch_without_prefix[: -len("-master")]
    return base_branch.rsplit("/", 1)[-1]


def base_branch_for_version(version_label: str) -> str:
    normalized = version_label if version_label.startswith("v") else f"v{version_label}"
    return f"codex/{normalized}-master"


def workstream_branch_prefix(base_branch: str) -> str:
    version_label = version_label_from_base_branch(base_branch)
    return f"codex/{version_label}-"


def cleanup_directory_prefix(base_branch: str) -> str:
    version_label = version_label_from_base_branch(base_branch)
    return f"autoreport_{version_label}-"


def list_known_version_master_branches() -> list[str]:
    completed = run_git(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes/origin"]
    )
    if completed.returncode != 0:
        return []

    candidates: set[str] = set()
    for raw_line in completed.stdout.splitlines():
        branch = normalize_branch_name(raw_line.strip())
        if VERSION_MASTER_BRANCH_RE.fullmatch(branch):
            candidates.add(branch)
    return sorted(
        candidates,
        key=lambda branch: version_tuple(version_label_from_base_branch(branch)),
    )


def infer_active_base_branch() -> str:
    current_branch_completed = run_git(["branch", "--show-current"])
    if current_branch_completed.returncode == 0:
        current_branch = normalize_branch_name(current_branch_completed.stdout.strip())
        if VERSION_MASTER_BRANCH_RE.fullmatch(current_branch):
            return current_branch

    known_branches = list_known_version_master_branches()
    if known_branches:
        return known_branches[-1]

    return base_branch_for_version(read_package_version())


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
    base_branch: str | None = None,
    branch_prefix: str | None = None,
    exclude_branches: set[str] | None = None,
    exclude_patterns: tuple[str, ...] | None = None,
) -> list[Workstream]:
    resolved_base_branch = base_branch or infer_active_base_branch()
    resolved_branch_prefix = branch_prefix or workstream_branch_prefix(resolved_base_branch)
    default_exclude_branches = {resolved_base_branch}
    default_exclude_patterns = (
        f"{resolved_branch_prefix}bootstrap-*",
        f"{resolved_branch_prefix}salvage-*",
    )

    exclude_branch_set = set(default_exclude_branches)
    if exclude_branches:
        exclude_branch_set.update(exclude_branches)
    exclude_pattern_values = (
        default_exclude_patterns if exclude_patterns is None else exclude_patterns
    )

    completed = run_git(["worktree", "list", "--porcelain"])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Failed to list git worktrees.")

    workstreams: list[Workstream] = []
    for entry in parse_worktree_list(completed.stdout):
        branch_raw = entry.get("branch", "")
        branch = normalize_branch_name(branch_raw)
        if not branch_is_in_scope(
            branch,
            resolved_branch_prefix,
            exclude_branch_set,
            exclude_pattern_values,
        ):
            continue

        worktree_path = Path(entry["worktree"])
        config = load_local_workstream_config(worktree_path)
        if config.get("orchestration_enabled") is False:
            continue

        key = str(config.get("key") or derive_workstream_key(branch, resolved_branch_prefix))
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


def registered_worktree_paths() -> set[Path]:
    completed = run_git(["worktree", "list", "--porcelain"])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Failed to list git worktrees.")
    return {Path(entry["worktree"]).resolve() for entry in parse_worktree_list(completed.stdout)}


def discover_retired_sibling_directories(
    prefix: str | None = None,
    *,
    base_branch: str | None = None,
) -> list[Path]:
    resolved_prefix = prefix or cleanup_directory_prefix(base_branch or infer_active_base_branch())
    active_paths = registered_worktree_paths()
    retired: list[Path] = []
    for candidate in WORKSPACE_ROOT.iterdir():
        if not candidate.is_dir():
            continue
        if not candidate.name.startswith(resolved_prefix):
            continue
        resolved = candidate.resolve()
        if resolved in active_paths:
            continue
        retired.append(resolved)
    return sorted(retired)


def ensure_within_workspace(path: Path) -> Path:
    resolved = path.resolve()
    workspace_root = WORKSPACE_ROOT.resolve()
    if workspace_root not in resolved.parents:
        raise RuntimeError(f"Refusing to operate outside workspace root: {resolved}")
    return resolved


def directory_item_count(path: Path) -> int:
    resolved = ensure_within_workspace(path)
    try:
        return sum(1 for _ in resolved.iterdir())
    except FileNotFoundError:
        return 0


def delete_directory(path: Path) -> None:
    resolved = ensure_within_workspace(path)
    shutil.rmtree(resolved)
