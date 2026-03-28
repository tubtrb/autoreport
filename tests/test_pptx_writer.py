"""Tests for PowerPoint writer compatibility and template error handling."""

from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from autoreport.outputs.pptx_writer import (
    PowerPointWriter,
    TemplateCompatibilityError,
    TemplateLoadError,
    TemplateReadError,
)


TEST_TEMP_ROOT = Path("tests") / "_tmp"


def make_test_dir() -> Path:
    """Create a writable test directory inside the repository."""

    TEST_TEMP_ROOT.mkdir(exist_ok=True)
    test_dir = TEST_TEMP_ROOT / uuid4().hex
    test_dir.mkdir()
    return test_dir


class _FakeSlideShapes:
    def __init__(self, *, has_title: bool) -> None:
        self.title = object() if has_title else None


class _FakePlaceholder:
    def __init__(self, *, idx: int, placeholder_type: object) -> None:
        self.placeholder_format = SimpleNamespace(
            idx=idx,
            type=placeholder_type,
        )
        self.text_frame = object()
        self.width = 100
        self.height = 100
        self.left = 0
        self.top = 0


class _FakeSlide:
    def __init__(self, *, has_title: bool, has_placeholder: bool) -> None:
        self.shapes = _FakeSlideShapes(has_title=has_title)
        self._placeholders = (
            {1: _FakePlaceholder(idx=1, placeholder_type=PP_PLACEHOLDER.BODY)}
            if has_placeholder
            else {}
        )

    @property
    def placeholders(self) -> dict[int, object]:
        return self._placeholders


class _FakeSlides:
    def __init__(self, scenarios: list[tuple[bool, bool]]) -> None:
        self._scenarios = iter(scenarios)

    def add_slide(self, _layout: object) -> _FakeSlide:
        has_title, has_placeholder = next(self._scenarios)
        return _FakeSlide(
            has_title=has_title,
            has_placeholder=has_placeholder,
        )


class _FakeParagraph:
    def __init__(self) -> None:
        self.font = SimpleNamespace(name=None)


class _FakeTextFrame:
    def __init__(self) -> None:
        self.paragraphs = [_FakeParagraph()]


class _FakeLayoutPlaceholder:
    def __init__(self, *, idx: int, placeholder_type: object, width: int) -> None:
        self.placeholder_format = SimpleNamespace(
            idx=idx,
            type=placeholder_type,
        )
        self.text_frame = _FakeTextFrame()
        self.width = width
        self.height = 100
        self.left = 0
        self.top = 0


class _FakeLayout:
    def __init__(
        self,
        *,
        name: str,
        has_title: bool,
        has_secondary_text: bool,
    ) -> None:
        placeholders: list[_FakeLayoutPlaceholder] = []
        if has_title:
            placeholders.append(
                _FakeLayoutPlaceholder(
                    idx=0,
                    placeholder_type=PP_PLACEHOLDER.TITLE,
                    width=80,
                )
            )
        if has_secondary_text:
            placeholders.append(
                _FakeLayoutPlaceholder(
                    idx=1,
                    placeholder_type=PP_PLACEHOLDER.BODY,
                    width=120,
                )
            )
        self.name = name
        self.placeholders = placeholders


class _FakePresentation:
    def __init__(
        self,
        *,
        slide_layouts: list[object],
        scenarios: list[tuple[bool, bool]],
    ) -> None:
        self.slide_layouts = slide_layouts
        self.slides = _FakeSlides(scenarios)


class PowerPointWriterTestCase(unittest.TestCase):
    """Verify writer-level template compatibility and load errors."""

    def test_writer_rejects_template_without_required_layouts(self) -> None:
        writer = PowerPointWriter()
        presentation = _FakePresentation(
            slide_layouts=[
                _FakeLayout(
                    name="Title Slide",
                    has_title=True,
                    has_secondary_text=True,
                )
            ],
            scenarios=[(True, True)],
        )

        with self.assertRaises(TemplateCompatibilityError) as context:
            writer._ensure_weekly_template_compatibility(
                presentation,
                template_path=Path("template.pptx"),
            )

        self.assertIn("missing 'body' slide layout at index 1", str(context.exception))

    def test_writer_rejects_template_without_required_placeholder(self) -> None:
        writer = PowerPointWriter()
        presentation = _FakePresentation(
            slide_layouts=[
                _FakeLayout(
                    name="Title Slide",
                    has_title=True,
                    has_secondary_text=True,
                ),
                _FakeLayout(
                    name="Title and Content",
                    has_title=True,
                    has_secondary_text=False,
                ),
            ],
            scenarios=[(True, True), (True, False)],
        )

        with self.assertRaises(TemplateCompatibilityError) as context:
            writer._ensure_weekly_template_compatibility(
                presentation,
                template_path=Path("template.pptx"),
            )

        self.assertIn("has no secondary text placeholder", str(context.exception))

    def test_load_presentation_raises_template_load_error_for_invalid_file(self) -> None:
        writer = PowerPointWriter()
        test_dir = make_test_dir()
        try:
            template_path = test_dir / "invalid-template.pptx"
            template_path.write_text("not a pptx", encoding="utf-8")

            with self.assertRaises(TemplateLoadError):
                writer._load_presentation(template_path)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_load_presentation_raises_template_read_error_for_os_errors(self) -> None:
        writer = PowerPointWriter()
        test_dir = make_test_dir()
        try:
            template_path = test_dir / "template.pptx"
            Presentation().save(str(template_path))

            with patch(
                "autoreport.outputs.pptx_writer.Presentation",
                side_effect=PermissionError("locked"),
            ):
                with self.assertRaises(TemplateReadError):
                    writer._load_presentation(template_path)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
