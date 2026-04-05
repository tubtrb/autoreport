"""Quiet local launchers for the Autoreport web surfaces."""

from __future__ import annotations

import argparse

import uvicorn


SURFACE_TARGETS = {
    "public": "autoreport.web.app:app",
    "debug": "autoreport.web.debug_app:app",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an Autoreport web surface with quiet Ctrl-C shutdown.",
    )
    parser.add_argument(
        "surface",
        nargs="?",
        choices=tuple(SURFACE_TARGETS),
        default="public",
        help="Which web surface to run.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind socket to this host.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind socket to this port.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = SURFACE_TARGETS[args.surface]
    port = args.port
    if port is None:
        port = 8000 if args.surface == "public" else 8010

    try:
        uvicorn.run(
            target,
            host=args.host,
            port=port,
            reload=args.reload,
        )
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
