"""Quiet local launchers for the Autoreport web surfaces."""

from __future__ import annotations

import argparse
import contextlib
import signal
import threading

import uvicorn
from uvicorn.main import STARTUP_FAILURE
from uvicorn.server import HANDLED_SIGNALS
from uvicorn.supervisors import ChangeReload


SURFACE_TARGETS = {
    "public": "autoreport.web.app:app",
    "debug": "autoreport.web.debug_app:app",
}


class QuietServer(uvicorn.Server):
    """Suppress Python 3.14 signal re-raise tracebacks on clean shutdown."""

    @contextlib.contextmanager
    def capture_signals(self):
        if threading.current_thread() is not threading.main_thread():
            yield
            return
        original_handlers = {
            sig: signal.signal(sig, self.handle_exit) for sig in HANDLED_SIGNALS
        }
        try:
            yield
        finally:
            for sig, handler in original_handlers.items():
                signal.signal(sig, handler)


def run_server(*, target: str, host: str, port: int, reload: bool) -> None:
    config = uvicorn.Config(
        target,
        host=host,
        port=port,
        reload=reload,
    )
    server = QuietServer(config=config)
    if config.should_reload:
        sock = config.bind_socket()
        ChangeReload(config, target=server.run, sockets=[sock]).run()
    else:
        server.run()
    if not server.started and not config.should_reload:
        raise SystemExit(STARTUP_FAILURE)


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
        run_server(
            target=target,
            host=args.host,
            port=port,
            reload=args.reload,
        )
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
