"""Tests for the quiet local web launcher."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from autoreport.web.serve import main


class WebServeTestCase(unittest.TestCase):
    def test_main_runs_public_surface_by_default(self) -> None:
        with patch("autoreport.web.serve.uvicorn.run") as run_mock:
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once_with(
            "autoreport.web.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
        )

    def test_main_runs_debug_surface_with_default_debug_port(self) -> None:
        with patch("autoreport.web.serve.uvicorn.run") as run_mock:
            exit_code = main(["debug"])

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once_with(
            "autoreport.web.debug_app:app",
            host="0.0.0.0",
            port=8010,
            reload=False,
        )

    def test_main_swallows_keyboard_interrupt(self) -> None:
        with patch(
            "autoreport.web.serve.uvicorn.run",
            side_effect=KeyboardInterrupt,
        ):
            exit_code = main(["public", "--host", "127.0.0.1", "--port", "8123"])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
