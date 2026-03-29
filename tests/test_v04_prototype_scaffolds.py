"""Tests for minimal v0.4 prototype scaffold behavior."""

from __future__ import annotations

import unittest

from experiments.v04.prototypes.richer_layout_spike import (
    LayoutExperimentCase,
    describe_layout_gap,
)
from experiments.v04.prototypes.text_shaping_spike import (
    TextShapingInput,
    not_implemented_text_shaper,
)


class V04PrototypeScaffoldTestCase(unittest.TestCase):
    """Lock the lowest-level helper behavior in the incubator lane."""

    def test_describe_layout_gap_summarizes_case_shape(self) -> None:
        case = LayoutExperimentCase(
            slide_role="body",
            content_blocks=["a", "b", "c"],
            slot_count=2,
        )

        self.assertEqual(
            describe_layout_gap(case),
            "Role=body, blocks=3, slots=2",
        )

    def test_not_implemented_text_shaper_is_explicit_placeholder(self) -> None:
        payload = TextShapingInput(
            section_title="Highlights",
            bullets=["One", "Two"],
        )

        with self.assertRaisesRegex(
            NotImplementedError,
            "v0.4 text-shaping experiments are scaffolded but not implemented.",
        ):
            not_implemented_text_shaper(payload)


if __name__ == "__main__":
    unittest.main()
