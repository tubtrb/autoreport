from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.verif_test.chatgpt import close_chatgpt_session
from tests.verif_test.pipeline import DEFAULT_BASE_URL, execute_prompt_pack_run


DEFAULT_SESSION = "extai-chatgpt-spot"
DEFAULT_CHECKER_URL = "http://127.0.0.1:8000/api/manual-draft-check"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility wrapper for the shared manual AI regression runner. "
            "The canonical operator entrypoint is run_manual_ai_regression.ps1."
        )
    )
    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION,
        help="Canonical ChatGPT profile key and manual Chrome seed target.",
    )
    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Number of fresh-chat samples to collect.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Exact output directory for this compatibility run.",
    )
    parser.add_argument(
        "--prompt-pack",
        required=True,
        help="Path to a JSON prompt pack generated from the canonical case catalog.",
    )
    parser.add_argument(
        "--checker-url",
        default=DEFAULT_CHECKER_URL,
        help="Local manual draft checker endpoint.",
    )
    parser.add_argument(
        "--checker-mode",
        choices=("http", "local"),
        default="http",
        help="Use the restarted local HTTP app or the in-process local fallback.",
    )
    parser.add_argument(
        "--send-wait-seconds",
        type=float,
        default=0.8,
        help="Delay after typing before clicking send.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=3.0,
        help="Polling interval while waiting for a response.",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=20,
        help="Maximum response polls per sample.",
    )
    return parser.parse_args()


def _base_url_from_checker_url(checker_url: str) -> str:
    suffix = "/api/manual-draft-check"
    if checker_url.endswith(suffix):
        return checker_url[: -len(suffix)]
    return DEFAULT_BASE_URL


def main() -> int:
    args = parse_args()
    try:
        run_dir = execute_prompt_pack_run(
            prompt_pack_path=Path(args.prompt_pack).resolve(),
            count=args.count,
            session=args.session,
            mode=args.checker_mode,
            output_dir=Path(args.output_dir).resolve(),
            base_url=_base_url_from_checker_url(args.checker_url),
            send_wait_seconds=args.send_wait_seconds,
            poll_seconds=args.poll_seconds,
            max_polls=args.max_polls,
            progress=lambda message: print(message, flush=True),
        )
        print(run_dir)
        return 0
    finally:
        close_chatgpt_session(args.session)


if __name__ == "__main__":
    raise SystemExit(main())
