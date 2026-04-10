from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workstream_runtime import (
    WORKSPACE_ROOT,
    cleanup_directory_prefix,
    delete_directory,
    directory_item_count,
    discover_retired_sibling_directories,
    infer_active_base_branch,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List or delete retired sibling worktree directories that are no longer registered with git."
    )
    default_prefix = cleanup_directory_prefix(infer_active_base_branch())
    parser.add_argument(
        "--prefix",
        default=default_prefix,
        help="Directory name prefix to inspect under the workspace root. Defaults to the inferred active version prefix.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete retired directories that match the prefix and are no longer registered worktrees.",
    )
    parser.add_argument(
        "--allow-nonempty",
        action="store_true",
        help="Also delete non-empty retired directories. Without this flag, non-empty candidates are reported as blockers only.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result.",
    )
    return parser.parse_args()


def build_candidate_records(prefix: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in discover_retired_sibling_directories(prefix):
        item_count = directory_item_count(path)
        records.append(
            {
                "path": str(path),
                "item_count": item_count,
                "empty": item_count == 0,
            }
        )
    return records


def delete_candidates(
    records: list[dict[str, object]],
    *,
    allow_nonempty: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    deleted: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    for record in records:
        path = Path(str(record["path"]))
        empty = bool(record["empty"])
        if not empty and not allow_nonempty:
            blocked.append(
                {
                    **record,
                    "reason": "Directory is not empty. Re-run with --allow-nonempty after review if deletion is intended.",
                }
            )
            continue
        try:
            delete_directory(path)
        except OSError as exc:
            blocked.append(
                {
                    **record,
                    "reason": f"Deletion failed: {exc}",
                }
            )
            continue
        deleted.append(record)
    return deleted, blocked


def main() -> int:
    args = parse_args()
    records = build_candidate_records(args.prefix)
    deleted: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    if args.delete:
        deleted, blocked = delete_candidates(records, allow_nonempty=args.allow_nonempty)
    payload = {
        "workspace_root": str(WORKSPACE_ROOT),
        "prefix": args.prefix,
        "delete_requested": args.delete,
        "allow_nonempty": args.allow_nonempty,
        "candidates": records,
        "deleted": deleted,
        "blocked": blocked,
    }
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0 if not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
