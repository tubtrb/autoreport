"""Tests for YAML loading behavior."""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import yaml

from autoreport.loader import load_yaml, parse_yaml_text


TEST_TEMP_ROOT = Path("tests") / "_tmp"


def make_test_dir() -> Path:
    """Create a writable test directory inside the repository."""

    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


class LoaderTestCase(unittest.TestCase):
    """Verify raw YAML loading and loader-level failures."""

    def test_load_yaml_returns_raw_mapping(self) -> None:
        test_dir = make_test_dir()
        try:
            report_path = test_dir / "report.yaml"
            report_path.write_text("title: Weekly Report\nteam: Platform Team\n", encoding="utf-8")

            loaded = load_yaml(report_path)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertEqual(
            loaded,
            {
                "title": "Weekly Report",
                "team": "Platform Team",
            },
        )

    def test_load_yaml_raises_file_not_found_for_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_yaml("does-not-exist.yaml")

    def test_load_yaml_raises_yaml_error_for_invalid_content(self) -> None:
        test_dir = make_test_dir()
        try:
            report_path = test_dir / "broken.yaml"
            report_path.write_text("title: [broken", encoding="utf-8")

            with self.assertRaises(yaml.YAMLError):
                load_yaml(report_path)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_load_yaml_raises_os_error_when_file_cannot_be_read(self) -> None:
        test_dir = make_test_dir()
        try:
            report_path = test_dir / "report.yaml"
            report_path.write_text("title: Weekly Report\n", encoding="utf-8")

            with patch("pathlib.Path.open", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    load_yaml(report_path)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_parse_yaml_text_returns_raw_mapping(self) -> None:
        loaded = parse_yaml_text("title: Weekly Report\nteam: Platform Team\n")

        self.assertEqual(
            loaded,
            {
                "title": "Weekly Report",
                "team": "Platform Team",
            },
        )

    def test_parse_yaml_text_raises_yaml_error_for_invalid_content(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            parse_yaml_text("title: [broken")


if __name__ == "__main__":
    unittest.main()
