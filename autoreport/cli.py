"""Command-line interface for the autoreport package.

The CLI remains intentionally small in v0.1. It validates YAML report inputs
for the weekly report schema without generating output files yet.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import yaml

from autoreport.loader import load_yaml
from autoreport.validator import ValidationError, validate_report


SUCCESS_LINES = (
    "Report input validated successfully.",
    "Generation not implemented yet.",
)


def build_parser() -> argparse.ArgumentParser:
    """Create the root argument parser for the console application."""
    parser = argparse.ArgumentParser(
        prog="autoreport",
        description="Generate structured reports from YAML inputs.",
    )
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate a report from a YAML definition file.",
    )
    generate_parser.add_argument(
        "report_path",
        help="Path to the YAML report definition.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        report_path = args.report_path

        try:
            raw_data = load_yaml(report_path)
            validate_report(raw_data)
        except FileNotFoundError:
            print(f"Report file not found: {report_path}", file=sys.stderr)
            return 1
        except OSError:
            print(f"Could not read report file: {report_path}", file=sys.stderr)
            return 1
        except yaml.YAMLError as exc:
            print(f"Failed to parse YAML: {exc}", file=sys.stderr)
            return 1
        except ValidationError as exc:
            print("Report validation failed.", file=sys.stderr)
            for error in exc.errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        except Exception:
            print("An unexpected internal error occurred.", file=sys.stderr)
            return 2

        for line in SUCCESS_LINES:
            print(line)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
