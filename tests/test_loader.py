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

GEMINI_STYLE_REPORT_CONTENT = """
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: 지정학적 위기
      subtitle_1: |
        중동 지역 긴장 상태 분석
  slides:
    - pattern_id: text.editorial
      kind: text
      slots:
        title: 갈등의 근원
        body_1: |
          미국과 이란의 긴장은 장기적으로 누적되어 왔습니다.
""".strip()

MIXED_CHATGPT_STYLE_REPORT_CONTENT = """
report_content:
title_slide:
pattern_id: cover.editorial
slots:
title: 미국-이란 충돌과 중동 정세

```yaml
- pattern_id: text.editorial
  kind: text
  slots:
    title: 최근 전개와 핵심 쟁점
    body_1: |
      최근 충돌은 복합적으로 전개되고 있다.
```
""".strip()


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

    def test_parse_yaml_text_accepts_fenced_yaml_code_block(self) -> None:
        loaded = parse_yaml_text(
            """```yaml
title: Weekly Report
team: Platform Team
```"""
        )

        self.assertEqual(
            loaded,
            {
                "title": "Weekly Report",
                "team": "Platform Team",
            },
        )

    def test_parse_yaml_text_extracts_yaml_code_block_from_wrapped_text(self) -> None:
        loaded = parse_yaml_text(
            """Here is the draft:

```yaml
title: Weekly Report
team: Platform Team
```

Use it directly.
"""
        )

        self.assertEqual(
            loaded,
            {
                "title": "Weekly Report",
                "team": "Platform Team",
            },
        )

    def test_parse_yaml_text_accepts_gemini_style_ai_report_content(self) -> None:
        loaded = parse_yaml_text(GEMINI_STYLE_REPORT_CONTENT)

        self.assertEqual(loaded["report_content"]["title_slide"]["pattern_id"], "cover.editorial")
        self.assertEqual(len(loaded["report_content"]["slides"]), 1)

    def test_parse_yaml_text_rejects_mixed_chatgpt_style_partial_fence_output(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            parse_yaml_text(MIXED_CHATGPT_STYLE_REPORT_CONTENT)

    def test_parse_yaml_text_raises_yaml_error_for_invalid_content(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            parse_yaml_text("title: [broken")


if __name__ == "__main__":
    unittest.main()
