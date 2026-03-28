"""Tests for contract-first Autoreport validation rules."""

from __future__ import annotations

import unittest
from pathlib import Path

from autoreport.models import ReportPayload, TemplateContract
from autoreport.loader import load_yaml
from autoreport.template_flow import get_built_in_contract
from autoreport.validator import (
    ValidationError,
    validate_payload,
    validate_template_contract,
)


def build_valid_payload() -> dict[str, object]:
    return {
        "report_payload": {
            "payload_version": "autoreport.payload.v1",
            "template_id": "autoreport-editorial-v1",
            "title_slide": {
                "title": "Autoreport",
                "subtitle": ["Template-aware PPTX autofill engine"],
            },
            "contents": {"enabled": True},
            "slides": [
                {
                    "kind": "text",
                    "title": "What It Does",
                    "include_in_contents": True,
                    "body": [
                        "Generate editable PowerPoint decks from structured inputs.",
                    ],
                    "slot_overrides": {},
                },
                {
                    "kind": "metrics",
                    "title": "Adoption Snapshot",
                    "include_in_contents": True,
                    "items": [
                        {"label": "Templates profiled", "value": 12},
                    ],
                    "slot_overrides": {},
                },
            ],
        }
    }


class ValidatorTestCase(unittest.TestCase):
    """Verify template-contract and payload validation behavior."""

    def test_validate_template_contract_accepts_built_in_contract(self) -> None:
        contract = validate_template_contract(get_built_in_contract().to_dict())

        self.assertIsInstance(contract, TemplateContract)
        self.assertEqual(contract.template_id, "autoreport-editorial-v1")
        self.assertEqual(
            [pattern.kind for pattern in contract.slide_patterns],
            ["text", "metrics", "text_image"],
        )

    def test_validate_payload_accepts_editorial_text_and_metrics_payload(self) -> None:
        payload = validate_payload(
            build_valid_payload(),
            get_built_in_contract(),
        )

        self.assertIsInstance(payload, ReportPayload)
        self.assertEqual(payload.template_id, "autoreport-editorial-v1")
        self.assertEqual([slide.kind for slide in payload.slides], ["text", "metrics"])

    def test_validate_payload_collects_expected_errors_for_invalid_payload(self) -> None:
        with self.assertRaises(ValidationError) as context:
            validate_payload(
                {
                    "report_payload": {
                        "payload_version": "wrong",
                        "template_id": "wrong-template",
                        "title_slide": {
                            "title": "   ",
                            "subtitle": [],
                        },
                        "contents": {"enabled": "yes"},
                        "slides": [
                            {
                                "kind": "oops",
                                "title": "  ",
                                "include_in_contents": "yes",
                                "body": [],
                                "slot_overrides": [],
                            }
                        ],
                    }
                },
                get_built_in_contract(),
            )

        self.assertEqual(
            context.exception.errors,
            [
                "Field 'payload_version' must equal 'autoreport.payload.v1'.",
                "Field 'template_id' must match 'autoreport-editorial-v1'.",
                "Field 'title_slide.title' must be a non-empty string.",
                "Field 'title_slide.subtitle' must contain at least 1 item.",
                "Field 'contents.enabled' must be a boolean.",
                "Field 'slides[0].title' must be a non-empty string.",
                "Field 'slides[0].include_in_contents' must be a boolean.",
                "Field 'slides[0].kind' must be one of 'text', 'metrics', or 'text_image'.",
                "Field 'slides[0].slot_overrides' must be an object.",
            ],
        )

    def test_validate_payload_rejects_unknown_slot_override_and_missing_image_ref(self) -> None:
        with self.assertRaises(ValidationError) as context:
            validate_payload(
                {
                    "report_payload": {
                        "payload_version": "autoreport.payload.v1",
                        "template_id": "autoreport-editorial-v1",
                        "title_slide": {
                            "title": "Autoreport",
                            "subtitle": ["Template-aware PPTX autofill engine"],
                        },
                        "contents": {"enabled": True},
                        "slides": [
                            {
                                "kind": "text_image",
                                "title": "Why It Matters",
                                "include_in_contents": True,
                                "body": ["Teams keep their own template language."],
                                "image": {"ref": "image_1", "fit": "contain"},
                                "caption": "Workflow preview",
                                "slot_overrides": {
                                    "text_image.unknown": {"text": "bad"}
                                },
                            }
                        ],
                    }
                },
                get_built_in_contract(),
                available_image_refs=(),
            )

        self.assertEqual(
            context.exception.errors,
            [
                "Field 'slides[0].image.ref' does not match a provided image reference.",
                "Field 'slides[0].slot_overrides.text_image.unknown' targets an unknown slot for the selected pattern.",
            ],
        )

    def test_validate_payload_accepts_yaml_example_file(self) -> None:
        payload = validate_payload(
            load_yaml(Path("examples") / "report_payload.yaml"),
            get_built_in_contract(),
        )

        self.assertEqual(payload.template_id, "autoreport-editorial-v1")
        self.assertEqual(
            payload.title_slide.subtitle,
            [
                "Template-aware PPTX autofill engine",
                "Turn one template into repeatable decks",
            ],
        )
        self.assertEqual(payload.slides[0].title, "Why Teams Use Autoreport")
        self.assertEqual(payload.slides[1].kind, "metrics")

    def test_validate_payload_accepts_json_example_file(self) -> None:
        payload = validate_payload(
            load_yaml(Path("examples") / "report_payload.json"),
            get_built_in_contract(),
        )

        self.assertEqual(payload.template_id, "autoreport-editorial-v1")
        self.assertEqual(payload.slides[1].title, "Adoption Snapshot")
        self.assertEqual(payload.slides[2].title, "Demo Surfaces")


if __name__ == "__main__":
    unittest.main()
