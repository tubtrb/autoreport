from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.verif_test.chatgpt import close_chatgpt_session
from tests.verif_test.pipeline import DEFAULT_BASE_URL
from tests.verif_test.release_gate import execute_release_gate_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the low-trigger single-session ChatGPT web release gate and write "
            "structured artifacts under output/verif_test."
        )
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
        help="Maximum response polls per case.",
    )
    parser.add_argument(
        "--session-check-only",
        action="store_true",
        help="Validate only the manually opened seeded ChatGPT session and skip the 20-chat release gate.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        run_dir = execute_release_gate_run(
            session=args.session,
            mode=args.mode,
            output_root=Path(args.output_root),
            base_url=args.base_url,
            send_wait_seconds=args.send_wait_seconds,
            poll_seconds=args.poll_seconds,
            max_polls=args.max_polls,
            session_check_only=args.session_check_only,
            progress=lambda message: print(message, flush=True),
        )
        summary_path = run_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(f"[release-gate] overall_status={summary['overall_status']}", flush=True)
        print(f"[release-gate] summary={summary_path}", flush=True)
        print(run_dir, flush=True)
        return 1 if summary["overall_status"] == "FAIL" else 0
    finally:
        close_chatgpt_session(args.session)


if __name__ == "__main__":
    raise SystemExit(main())
