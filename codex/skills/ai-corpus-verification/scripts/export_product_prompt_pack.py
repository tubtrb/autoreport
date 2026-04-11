from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


DEFAULT_APP_PATH = Path("autoreport/web/app.py")
DEFAULT_OUTPUT_PATH = Path(
    "codex/skills/ai-corpus-verification/references/chatgpt-product-full-prompt-pack.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the default production-faithful ChatGPT prompt pack from "
            "autoreport/web/app.py."
        )
    )
    parser.add_argument(
        "--app-path",
        default=str(DEFAULT_APP_PATH),
        help="Path to autoreport/web/app.py.",
    )
    parser.add_argument(
        "--output-path",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to write the exported prompt pack JSON.",
    )
    return parser.parse_args()


def extract_manual_draft_prompt_yaml(app_path: Path) -> str:
    module = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "MANUAL_DRAFT_PROMPT_YAML":
                value_node = node.value
                if (
                    isinstance(value_node, ast.Call)
                    and isinstance(value_node.func, ast.Attribute)
                    and value_node.func.attr == "strip"
                    and not value_node.args
                    and not value_node.keywords
                ):
                    value_node = value_node.func.value
                value = ast.literal_eval(value_node)
                if not isinstance(value, str):
                    raise RuntimeError("MANUAL_DRAFT_PROMPT_YAML is not a string literal.")
                return value.strip()
    raise RuntimeError("Could not find MANUAL_DRAFT_PROMPT_YAML in app.py.")


def main() -> int:
    args = parse_args()
    app_path = Path(args.app_path).resolve()
    output_path = Path(args.output_path).resolve()

    prompt = extract_manual_draft_prompt_yaml(app_path)
    payload = [
        {
            "prompt_id": "gpt-product-full",
            "label": "product_full_manual_comments",
            "strength": "product",
            "prompt": prompt,
        }
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
