from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.verif_test.catalog import DEFAULT_SUITE_NAME, build_prompt_pack_payload


DEFAULT_APP_PATH = Path("autoreport/web/app.py")
DEFAULT_OUTPUT_PATH = Path(
    "codex/skills/ai-corpus-verification/references/chatgpt-product-full-prompt-pack.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the canonical production-faithful manual AI regression prompt pack "
            "from tests/verif_test/cases/manual_public_cases.yaml."
        )
    )
    parser.add_argument(
        "--app-path",
        default=str(DEFAULT_APP_PATH),
        help="Compatibility-only argument retained for older scripts. The prompt pack now comes from the case catalog.",
    )
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to write the exported prompt pack JSON.",
    )
    parser.add_argument(
        "--suite",
        default=DEFAULT_SUITE_NAME,
        choices=("smoke", "regression", "full"),
        help="Canonical case suite to export.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output_path).resolve()
    payload = build_prompt_pack_payload(suite_name=args.suite)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
