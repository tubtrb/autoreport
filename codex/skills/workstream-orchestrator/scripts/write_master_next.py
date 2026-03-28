from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
WORKSPACE_ROOT = REPO_ROOT.parent
WORKSTREAM_FOLDERS = {
    "template-contract-export": "autoreport_v0.3-template-contract-export",
    "generic-payload-schema": "autoreport_v0.3-generic-payload-schema",
    "text-layout-engine": "autoreport_v0.3-text-layout-engine",
    "image-layout-engine": "autoreport_v0.3-image-layout-engine",
    "cli-web-template-flow": "autoreport_v0.3-cli-web-template-flow",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write master-thread next-step instructions into sibling worktree .codex files."
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

    normalized: dict[str, str] = {}
    for key, value in payload.items():
        if key not in WORKSTREAM_FOLDERS:
            raise SystemExit(f"Unknown workstream key: {key}")
        if not isinstance(value, str):
            raise SystemExit(f"Instruction for {key} must be a string.")
        normalized[key] = value.rstrip() + "\n"
    return normalized


def list_targets(filename: str) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    for key, folder in WORKSTREAM_FOLDERS.items():
        target = WORKSPACE_ROOT / folder / ".codex" / filename
        targets.append({"key": key, "path": str(target)})
    return targets


def write_payload(payload: dict[str, str], filename: str) -> list[dict[str, object]]:
    writes: list[dict[str, object]] = []
    for key, text in payload.items():
        worktree = WORKSPACE_ROOT / WORKSTREAM_FOLDERS[key]
        if not worktree.exists():
            raise SystemExit(f"Missing worktree: {worktree}")
        codex_dir = worktree / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        target = codex_dir / filename
        target.write_text(text, encoding="utf-8")
        writes.append(
            {
                "key": key,
                "path": str(target),
                "bytes": len(text.encode("utf-8")),
            }
        )
    return writes


def main() -> int:
    args = parse_args()
    if args.list:
        json.dump(list_targets(args.filename), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    payload = load_payload(args)
    result = {"writes": write_payload(payload, args.filename)}
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
