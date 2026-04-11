"""Tests for the quiet local web launcher."""

from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock, patch

from autoreport.web.serve import QuietServer, main


class WebServeTestCase(unittest.TestCase):
    def test_main_runs_public_surface_by_default(self) -> None:
        with patch("autoreport.web.serve.run_server") as run_mock:
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once_with(
            target="autoreport.web.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
        )

    def test_main_runs_debug_surface_with_default_debug_port(self) -> None:
        with patch("autoreport.web.serve.run_server") as run_mock:
            exit_code = main(["debug"])

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once_with(
            target="autoreport.web.debug_app:app",
            host="0.0.0.0",
            port=8010,
            reload=False,
        )

    def test_main_swallows_keyboard_interrupt(self) -> None:
        with patch(
            "autoreport.web.serve.run_server",
            side_effect=KeyboardInterrupt,
        ):
            exit_code = main(["public", "--host", "127.0.0.1", "--port", "8123"])

        self.assertEqual(exit_code, 0)

    def test_quiet_server_does_not_reraise_captured_signals(self) -> None:
        server = QuietServer(config=MagicMock())
        server.handle_exit = MagicMock()
        server._captured_signals = [2]

        with (
            patch("autoreport.web.serve.threading.current_thread", return_value=threading.main_thread()),
            patch("autoreport.web.serve.signal.signal", return_value=MagicMock()),
            patch("autoreport.web.serve.signal.raise_signal") as raise_signal_mock,
        ):
            with server.capture_signals():
                pass

        raise_signal_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
