from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.verif_test.pipeline import recheck_saved_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay saved manual YAML corpus artifacts through the shared manual AI verification pipeline."
        )
    )
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Artifact directory containing per-sample folders with yaml-candidate.yaml.",
    )
    parser.add_argument(
        "--built-in",
        default="autoreport_manual",
        help="Compatibility-only argument retained for older scripts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = recheck_saved_artifacts(artifact_dir=Path(args.artifact_dir))
    print(Path(args.artifact_dir).resolve() / "recheck-summary.txt")
    print(
        json.dumps(
            {
                "artifact_dir": str(Path(args.artifact_dir).resolve()),
                "category_counts": summary["category_counts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
