"""Command-line interface for the autoreport package."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from autoreport.engine.generator import generate_report
from autoreport.models import ReportRequest
from autoreport.outputs.pptx_writer import (
    OutputWriteError,
    TemplateCompatibilityError,
    TemplateLoadError,
    TemplateNotFoundError,
    TemplateReadError,
)
from autoreport.validator import ValidationError


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
    generate_parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        help="Path to the generated PowerPoint file.",
    )
    generate_parser.add_argument(
        "--template",
        dest="template_path",
        help="Optional PowerPoint template path.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        report_path = args.report_path

        try:
            output_path = generate_report(
                ReportRequest(
                    source_path=Path(report_path),
                    output_path=(
                        Path(args.output_path) if args.output_path else None
                    ),
                    template_path=(
                        Path(args.template_path) if args.template_path else None
                    ),
                )
            )
        except TemplateNotFoundError as exc:
            print(f"Template file not found: {exc.template_path}", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"Report file not found: {report_path}", file=sys.stderr)
            return 1
        except TemplateLoadError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except TemplateReadError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except TemplateCompatibilityError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except OutputWriteError as exc:
            print(f"Could not write report file: {exc.output_path}", file=sys.stderr)
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

        print(f"Report generated successfully: {output_path}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
