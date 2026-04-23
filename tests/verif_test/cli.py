from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.verif_test.chatgpt import close_chatgpt_session
from tests.verif_test.pipeline import DEFAULT_BASE_URL, execute_suite_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the canonical manual AI regression suite against the public manual flow "
            "and write structured verification artifacts under output/verif_test."
        )
    )
    parser.add_argument(
        "--suite",
        choices=("smoke", "regression", "full"),
        required=True,
        help="Named verification suite from tests/verif_test/cases/manual_public_cases.yaml.",
    )
    parser.add_argument(
        "--session",
        default="extai-chatgpt-spot",
        help="Canonical ChatGPT profile key and manual Chrome seed target.",
    )
    parser.add_argument(
        "--mode",
        choices=("http", "local"),
        default="http",
        help="Use the restarted local HTTP app or the in-process local fallback.",
    )
    parser.add_argument(
        "--output-root",
        default="output/verif_test",
        help="Root folder under which a timestamped run directory will be created.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Public local app base URL when --mode=http.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=None,
        help="Optional compatibility override that cycles through the selected suite until this many samples are collected.",
    )
    parser.add_argument(
        "--send-wait-seconds",
        type=float,
        default=0.8,
        help="Delay after typing before clicking send in ChatGPT.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=3.0,
        help="Response poll interval while waiting for a ChatGPT reply.",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=20,
        help="Maximum response polls per sample.",
    )
    parser.add_argument(
        "--session-check-only",
        action="store_true",
        help="Validate only the manually opened ChatGPT session and skip preflight, health, and case execution.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_dir = execute_suite_run(
            suite_name=args.suite,
            session=args.session,
            mode=args.mode,
            output_root=Path(args.output_root),
            base_url=args.base_url,
            sample_count=args.sample_count,
            send_wait_seconds=args.send_wait_seconds,
            poll_seconds=args.poll_seconds,
            max_polls=args.max_polls,
            session_check_only=args.session_check_only,
            progress=lambda message: print(message, flush=True),
        )
        summary_path = run_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(f"[manual-ai] overall_status={summary['overall_status']}", flush=True)
        print(f"[manual-ai] summary={summary_path}", flush=True)
        print(run_dir, flush=True)
        return 1 if summary["overall_status"] == "FAIL" else 0
    finally:
        close_chatgpt_session(args.session)


if __name__ == "__main__":
    raise SystemExit(main())
