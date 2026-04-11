from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workstream_runtime import discover_workstreams, infer_active_base_branch

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write master-thread next-step instructions into discovered task worktree .codex files."
    )
    parser.add_argument(
        "--base-branch",
        default=infer_active_base_branch(),
        help="Version-master branch whose child workstreams should be discovered. Defaults to the inferred active version-master branch.",
    )
    parser.add_argument(
        "--stdin-json",
        action="store_true",
        help="Read a JSON object of {workstream_key: instruction_text} from stdin.",
    )
    parser.add_argument(
        "--json-file",
        help="Read a JSON object of {workstream_key: instruction_text} from a file.",
    )
    parser.add_argument(
        "--filename",
        default="master-next.txt",
        help="Target filename under each worktree's .codex directory.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the known workstream keys and target paths as JSON.",
    )
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> dict[str, str]:
    if args.stdin_json == bool(args.json_file):
        raise SystemExit("Choose exactly one of --stdin-json or --json-file.")

    raw = sys.stdin.read() if args.stdin_json else Path(args.json_file).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise SystemExit("Instruction payload must be a JSON object.")

    workstreams = {item.key: item for item in discover_workstreams(base_branch=args.base_branch)}
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        if key not in workstreams:
            raise SystemExit(f"Unknown workstream key: {key}")
        if not isinstance(value, str):
            raise SystemExit(f"Instruction for {key} must be a string.")
        normalized[key] = value.rstrip() + "\n"
    return normalized


def list_targets(filename: str, base_branch: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for workstream in discover_workstreams(base_branch=base_branch):
        target = workstream.path / ".codex" / filename
        targets.append({"key": workstream.key, "branch": workstream.branch, "path": str(target)})
    return targets


def write_payload(payload: dict[str, str], filename: str, base_branch: str) -> list[dict[str, object]]:
    writes: list[dict[str, object]] = []
    workstreams = {item.key: item for item in discover_workstreams(base_branch=base_branch)}
    for key, text in payload.items():
        worktree = workstreams[key].path
        if not worktree.exists():
            raise SystemExit(f"Missing worktree: {worktree}")
        codex_dir = worktree / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        target = codex_dir / filename
        target.write_text(text, encoding="utf-8")
        writes.append(
            {
                "key": key,
                "branch": workstreams[key].branch,
                "path": str(target),
                "bytes": len(text.encode("utf-8")),
            }
        )
    return writes


def main() -> int:
    args = parse_args()
    if args.list:
        json.dump(list_targets(args.filename, args.base_branch), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    payload = load_payload(args)
    result = {"base_branch": args.base_branch, "writes": write_payload(payload, args.filename, args.base_branch)}
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
