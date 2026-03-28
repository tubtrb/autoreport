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
from autoreport.templates.autofill import (
    FillPlan,
    FitResult,
    FitStatus,
    PlannedSlide,
    SlotContentKind,
    SlotDescriptor,
)
from autoreport.templates.weekly_report import profile_weekly_template


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
    def __init__(
        self,
        *,
        idx: int,
        placeholder_type: object,
        width: int,
        top: int = 0,
        left: int = 0,
        height: int = 100,
    ) -> None:
        self.placeholder_format = SimpleNamespace(
            idx=idx,
            type=placeholder_type,
        )
        self.text_frame = _FakeTextFrame()
        self.width = width
        self.height = height
        self.left = left
        self.top = top


class _FakeLayout:
    def __init__(
        self,
        *,
        name: str,
        has_title: bool = False,
        has_secondary_text: bool = False,
        placeholders: list[_FakeLayoutPlaceholder] | None = None,
    ) -> None:
        resolved_placeholders = list(placeholders or [])
        if not resolved_placeholders and has_title:
            resolved_placeholders.append(
                _FakeLayoutPlaceholder(
                    idx=0,
                    placeholder_type=PP_PLACEHOLDER.TITLE,
                    width=80,
                )
            )
        if not placeholders and has_secondary_text:
            resolved_placeholders.append(
                _FakeLayoutPlaceholder(
                    idx=1,
                    placeholder_type=PP_PLACEHOLDER.BODY,
                    width=120,
                )
            )
        self.name = name
        self.placeholders = resolved_placeholders


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

        self.assertIn(
            "no compatible body layout exposing both title and content placeholders",
            str(context.exception),
        )

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

        self.assertIn(
            "no compatible body layout exposing both title and content placeholders",
            str(context.exception),
        )

    def test_profile_weekly_template_accepts_nonstandard_layout_indices(self) -> None:
        presentation = _FakePresentation(
            slide_layouts=[
                _FakeLayout(
                    name="Corporate Title",
                    placeholders=[
                        _FakeLayoutPlaceholder(
                            idx=12,
                            placeholder_type=PP_PLACEHOLDER.BODY,
                            width=120,
                            top=100,
                        ),
                        _FakeLayoutPlaceholder(
                            idx=13,
                            placeholder_type=PP_PLACEHOLDER.BODY,
                            width=800,
                            top=900,
                            height=300,
                        ),
                        _FakeLayoutPlaceholder(
                            idx=14,
                            placeholder_type=PP_PLACEHOLDER.BODY,
                            width=260,
                            top=3200,
                            height=900,
                        ),
                    ],
                ),
                _FakeLayout(
                    name="Contents",
                    placeholders=[
                        _FakeLayoutPlaceholder(
                            idx=1,
                            placeholder_type=PP_PLACEHOLDER.BODY,
                            width=1000,
                            top=700,
                            height=3600,
                        )
                    ],
                ),
                _FakeLayout(name="Blank"),
                _FakeLayout(
                    name="Title and Content",
                    placeholders=[
                        _FakeLayoutPlaceholder(
                            idx=0,
                            placeholder_type=PP_PLACEHOLDER.TITLE,
                            width=1000,
                            top=100,
                            height=250,
                        ),
                        _FakeLayoutPlaceholder(
                            idx=1,
                            placeholder_type=PP_PLACEHOLDER.BODY,
                            width=1000,
                            top=900,
                            height=3800,
                        ),
                    ],
                ),
            ],
            scenarios=[],
        )

        profile = profile_weekly_template(
            presentation,
            template_path=Path("corporate-template.pptx"),
        )

        self.assertEqual(profile.title_layout_index, 0)
        self.assertEqual(profile.body_layout_index, 3)
        self.assertEqual(profile.title_slot.placeholder_index, 13)
        self.assertEqual(profile.subtitle_slot.placeholder_index, 14)
        self.assertEqual(profile.body_title_slot.placeholder_index, 0)
        self.assertEqual(profile.body_content_slot.placeholder_index, 1)

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

    def test_write_fill_plan_supports_text_box_slots(self) -> None:
        writer = PowerPointWriter()
        test_dir = make_test_dir()
        try:
            output_path = test_dir / "textbox-template-output.pptx"
            presentation = Presentation()
            fill_plan = FillPlan(
                slides=[
                    PlannedSlide(
                        layout_name="Blank",
                        layout_index=6,
                        title_slot=SlotDescriptor(
                            slot_name="title",
                            layout_index=6,
                            placeholder_index=None,
                            x=600000,
                            y=700000,
                            width=9000000,
                            height=700000,
                            preferred_font_size=28,
                            min_font_size=20,
                            allowed_kinds=(SlotContentKind.TITLE,),
                        ),
                        title_text="Weekly Report",
                        content_kind=SlotContentKind.TITLE,
                        source_block_id="title",
                        body_slot=SlotDescriptor(
                            slot_name="subtitle",
                            layout_index=6,
                            placeholder_index=None,
                            x=600000,
                            y=1800000,
                            width=3500000,
                            height=1200000,
                            preferred_font_size=18,
                            min_font_size=14,
                            allowed_kinds=(SlotContentKind.SHORT_FACT_OR_STATUS,),
                        ),
                        subtitle_text="Platform Team\n2026-W24",
                        title_font_size=28,
                        body_font_size=18,
                        fit_result=FitResult(
                            status=FitStatus.FIT,
                            font_size=18,
                            consumed_items=1,
                            remaining_items=0,
                        ),
                    )
                ]
            )

            writer.write_fill_plan(
                presentation=presentation,
                output_path=output_path,
                fill_plan=fill_plan,
            )

            written = Presentation(str(output_path))
            slide_texts = [
                shape.text
                for shape in written.slides[0].shapes
                if hasattr(shape, "text") and shape.text
            ]
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

        self.assertIn("Weekly Report", slide_texts)
        self.assertIn("Platform Team\n2026-W24", slide_texts)
