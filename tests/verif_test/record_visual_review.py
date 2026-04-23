from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.verif_test.pipeline import record_visual_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Record the fixed representative visual review decision for a manual AI regression run "
            "and refresh summary/review queue artifacts in place."
        )
    )
    parser.add_argument("--run-dir", required=True, help="Run directory under output/verif_test.")
    parser.add_argument("--case-id", required=True, help="Representative case ID to mark as reviewed.")
    parser.add_argument(
        "--decision",
        choices=("pass", "fail"),
        required=True,
        help="Visual review decision for the representative case.",
    )
    parser.add_argument(
        "--note",
        default="",
        help="Optional short note explaining the review outcome.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    refreshed = record_visual_review(
        run_dir=Path(args.run_dir),
        case_id=args.case_id,
        decision=args.decision,
        note=args.note,
    )
    print(Path(args.run_dir).resolve())
    print(refreshed["overall_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
