"""Command-line interface for the autoreport package."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from autoreport.engine.generator import generate_report
from autoreport.models import ReportRequest
from autoreport.outputs.pptx_writer import (
    OutputWriteError,
    TemplateLoadError,
    TemplateNotFoundError,
    TemplateReadError,
)
from autoreport.template_flow import (
    PUBLIC_BUILT_IN_TEMPLATE_NAME,
    inspect_template_contract,
    load_template_contract,
    scaffold_payload,
    serialize_document,
)
from autoreport.validator import ValidationError


def build_parser() -> argparse.ArgumentParser:
    """Create the root argument parser for the console application."""

    parser = argparse.ArgumentParser(
        prog="autoreport",
        description="Inspect templates, scaffold payloads, and generate editable decks.",
    )
    subparsers = parser.add_subparsers(dest="command")

    inspect_parser = subparsers.add_parser(
        "inspect-template",
        help="Inspect a built-in or user-supplied template and export its contract.",
    )
    inspect_group = inspect_parser.add_mutually_exclusive_group()
    inspect_group.add_argument(
        "--template",
        dest="template_path",
        help="Path to a PowerPoint template file.",
    )
    inspect_group.add_argument(
        "--built-in",
        dest="built_in",
        default=PUBLIC_BUILT_IN_TEMPLATE_NAME,
        help="Built-in template name to inspect.",
    )
    inspect_parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
        help="Serialization format for the exported contract.",
    )
    inspect_parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        help="Optional output file path for the exported contract.",
    )

    scaffold_parser = subparsers.add_parser(
        "scaffold-payload",
        help="Generate a starter report payload from a template contract file.",
    )
    scaffold_parser.add_argument(
        "contract_path",
        help="Path to a template contract YAML or JSON file.",
    )
    scaffold_parser.add_argument(
        "--format",
        choices=("yaml", "json"),
        default="yaml",
        help="Serialization format for the starter payload.",
    )
    scaffold_parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        help="Optional output file path for the starter payload.",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate an Autoreport deck from a report payload file.",
    )
    generate_parser.add_argument(
        "payload_path",
        help="Path to the report payload YAML definition.",
    )
    generate_group = generate_parser.add_mutually_exclusive_group()
    generate_group.add_argument(
        "--template",
        dest="template_path",
        help="Path to a PowerPoint template file.",
    )
    generate_group.add_argument(
        "--built-in",
        dest="built_in",
        default=PUBLIC_BUILT_IN_TEMPLATE_NAME,
        help="Built-in template name to use for generation.",
    )
    generate_parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        help="Path to the generated PowerPoint file.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect-template":
            contract = inspect_template_contract(
                template_path=(
                    Path(args.template_path) if args.template_path else None
                ),
                built_in=args.built_in,
            )
            document = serialize_document(contract.to_dict(), fmt=args.format)
            _emit_document(document, output_path=args.output_path)
            return 0

        if args.command == "scaffold-payload":
            contract = load_template_contract(Path(args.contract_path))
            payload = scaffold_payload(contract)
            document = serialize_document(payload.to_dict(), fmt=args.format)
            _emit_document(document, output_path=args.output_path)
            return 0

        if args.command == "generate":
            output_path = generate_report(
                ReportRequest(
                    source_path=Path(args.payload_path),
                    output_path=(
                        Path(args.output_path) if args.output_path else None
                    ),
                    template_path=(
                        Path(args.template_path) if args.template_path else None
                    ),
                    template_name=args.built_in,
                )
            )
            print(f"Autoreport deck generated successfully: {output_path}")
            return 0
    except TemplateNotFoundError as exc:
        print(f"Template file not found: {exc.template_path}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Input file not found: {exc.filename}", file=sys.stderr)
        return 1
    except TemplateLoadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except TemplateReadError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OutputWriteError as exc:
        print(f"Could not write report file: {exc.output_path}", file=sys.stderr)
        return 1
    except OSError as exc:
        target = getattr(exc, "filename", None)
        if target is not None:
            print(f"Could not read input file: {target}", file=sys.stderr)
        else:
            print("Could not read the requested input file.", file=sys.stderr)
        return 1
    except yaml.YAMLError as exc:
        print(f"Failed to parse YAML: {exc}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print("Payload validation failed.", file=sys.stderr)
        for error in exc.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("An unexpected internal error occurred.", file=sys.stderr)
        return 2

    parser.print_help()
    return 0


def _emit_document(document: str, *, output_path: str | None) -> None:
    if output_path is None:
        print(document.rstrip())
        return

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(document, encoding="utf-8")
    print(f"Wrote output successfully: {target_path}")


if __name__ == "__main__":
    raise SystemExit(main())
