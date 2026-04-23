from __future__ import annotations

import unittest
import yaml

from autoreport.web.manual_ai_yaml import (
    coerce_manual_ai_yaml_candidate,
    parse_public_payload_yaml,
)
from autoreport.web.style_presets import MANUAL_PUBLIC_TEMPLATE_NAME


class ManualAiYamlCoercionTestCase(unittest.TestCase):
    def test_fenced_yaml_is_unwrapped(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            "```yaml\nreport_content:\n  title_slide:\n    pattern_id: cover.manual\n```",
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertEqual(
            result.normalized_yaml,
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                ]
            ),
        )
        self.assertIn("extracted_fenced_yaml", result.actions)

    def test_leading_and_trailing_prose_is_trimmed(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            (
                "Here is the completed draft.\n\n"
                "report_content:\n"
                "  title_slide:\n"
                "    pattern_id: cover.manual\n"
                "This matches the schema."
            ),
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertEqual(
            result.normalized_yaml,
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                ]
            ),
        )
        self.assertIn("trimmed_leading_prose", result.actions)
        self.assertIn("trimmed_trailing_prose", result.actions)

    def test_rootless_manual_yaml_is_wrapped_under_report_content(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            "\n".join(
                [
                    "title_slide:",
                    "  pattern_id: cover.manual",
                    "  slots:",
                    "    doc_title: Demo",
                ]
            ),
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertEqual(
            result.normalized_yaml,
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                    "    slots:",
                    "      doc_title: Demo",
                ]
            ),
        )
        self.assertIn("wrapped_report_content_root", result.actions)
        self.assertNotIn("image_2", result.normalized_yaml)

    def test_existing_valid_yaml_is_no_op(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                ]
            ),
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertEqual(result.actions, ())
        self.assertEqual(
            result.normalized_yaml,
            "\n".join(
                [
                    "report_content:",
                    "  title_slide:",
                    "    pattern_id: cover.manual",
                ]
            ),
        )

    def test_prose_only_answer_stays_failure(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            "Here is the completed draft in prose only.",
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertIsNone(result.normalized_yaml)

    def test_flattened_yaml_with_trailing_unclosed_quote_is_salvaged(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            "\n".join(
                [
                    "report_content:",
                    "title_slide:",
                    "pattern_id: cover.manual",
                    "slides:",
                    "pattern_id: text_image.manual.procedure.one",
                    "slots:",
                    "step_no: '1.1'",
                    "detail_body: 'Truncated value",
                ]
            ),
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertIsNotNone(result.normalized_yaml)
        self.assertIn("repaired_indentation", result.actions)
        self.assertIn("closed_trailing_quote", result.actions)
        self.assertIn("detail_body: 'Truncated value'", result.normalized_yaml)

    def test_flattened_yaml_with_wrapped_scalars_is_salvaged(self) -> None:
        result = coerce_manual_ai_yaml_candidate(
            "\n".join(
                [
                    "report_content:",
                    "title_slide:",
                    "pattern_id: cover.manual",
                    "slots:",
                    "doc_title: Demo",
                    "doc_subtitle: Wrapped subtitle value",
                    "that continues on the next line.",
                    "contents_slide:",
                    "pattern_id: contents.manual",
                    "slides:",
                    "pattern_id: text_image.manual.procedure.one",
                    "slots:",
                    "step_no: '1.1'",
                    "command_or_action: 'Action: validate the state and capture",
                    "the matching evidence screenshot.'",
                    "summary: Confirm the visible state with the required",
                    "screenshots.",
                    "detail_body: |-",
                    "Case demo uses the one-image pattern for this step.",
                    "Keep the note short.",
                    "image_1: image_1",
                    "caption_1: Demo screenshot",
                ]
            ),
            built_in=MANUAL_PUBLIC_TEMPLATE_NAME,
        )

        self.assertIsNotNone(result.normalized_yaml)
        self.assertIn("repaired_indentation", result.actions)
        self.assertIn("that continues on the next line.", result.normalized_yaml)
        self.assertIn("the matching evidence screenshot.'", result.normalized_yaml)
        self.assertIn("screenshots.", result.normalized_yaml)

    def test_parse_public_payload_yaml_rejects_empty_document(self) -> None:
        with self.assertRaises(yaml.YAMLError):
            parse_public_payload_yaml("", built_in=MANUAL_PUBLIC_TEMPLATE_NAME)


if __name__ == "__main__":
    unittest.main()
