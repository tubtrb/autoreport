"""Tests for template-aware autofill sizing and spill heuristics."""

from __future__ import annotations

import unittest

from autoreport.templates.autofill import (
    SlotContentKind,
    SlotDescriptor,
    estimate_item_line_usage,
    estimate_wrapped_line_count,
    fit_text_items_to_slot,
    FitStatus,
)


def make_slot(
    *,
    width: int,
    height: int,
    preferred_font_size: int = 18,
    min_font_size: int = 12,
) -> SlotDescriptor:
    return SlotDescriptor(
        slot_name="body",
        layout_index=1,
        placeholder_index=1,
        x=0,
        y=0,
        width=width,
        height=height,
        preferred_font_size=preferred_font_size,
        min_font_size=min_font_size,
        allowed_kinds=(
            SlotContentKind.PARAGRAPH_OR_BULLETS,
            SlotContentKind.SHORT_FACT_OR_STATUS,
        ),
    )


class AutofillHeuristicsTestCase(unittest.TestCase):
    """Lock the clean-room wrap and spill heuristics used by v0.3."""

    def test_estimate_wrapped_line_count_accounts_for_soft_wrap(self) -> None:
        self.assertEqual(estimate_wrapped_line_count("abcdefghij", 5), 2)

    def test_estimate_item_line_usage_counts_explicit_newlines(self) -> None:
        used_lines = estimate_item_line_usage(["abcde\nfghij"], chars_per_line=10)
        self.assertEqual(used_lines, 2)

    def test_fit_text_items_to_slot_spills_on_line_capacity(self) -> None:
        slot = make_slot(
            width=260 * 12700,
            height=110 * 12700,
            preferred_font_size=18,
            min_font_size=18,
        )
        fit_result = fit_text_items_to_slot(
            [
                "one " * 12,
                "two " * 12,
                "three " * 12,
            ],
            slot,
        )

        self.assertEqual(fit_result.status, FitStatus.SPILL)
        self.assertGreaterEqual(fit_result.consumed_items, 1)
        self.assertGreater(fit_result.remaining_items, 0)

    def test_fit_text_items_to_slot_flags_single_item_overflow(self) -> None:
        slot = make_slot(
            width=12 * 12700,
            height=24 * 12700,
            preferred_font_size=18,
            min_font_size=18,
        )
        fit_result = fit_text_items_to_slot(
            ["oversized " * 40],
            slot,
        )

        self.assertEqual(fit_result.status, FitStatus.OVERFLOW)
        self.assertTrue(fit_result.out_of_bounds_risk)
