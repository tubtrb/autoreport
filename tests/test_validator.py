"""Tests for contract-first Autoreport validation rules."""

from __future__ import annotations

import unittest

from autoreport.models import AuthoringPayload, ReportPayload, TemplateContract
from autoreport.template_flow import get_built_in_contract
from autoreport.validator import (
    ValidationError,
    validate_authoring_payload,
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


def build_valid_authoring_payload() -> dict[str, object]:
    return {
        "authoring_payload": {
            "payload_version": "autoreport.authoring.v1",
            "template_id": "autoreport-editorial-v1",
            "deck_context": {
                "audience": "executives",
                "tone": "concise",
            },
            "title_slide": {
                "title": "Autoreport",
                "subtitle": ["Template-aware PPTX autofill engine"],
            },
            "contents": {"enabled": True},
            "slides": [
                {
                    "slide_no": 1,
                    "goal": "What It Does",
                    "include_in_contents": True,
                    "context": {
                        "summary": "Generate editable PowerPoint decks from structured inputs.",
                        "bullets": ["Keep the authoring contract high-level."],
                    },
                    "layout_request": {
                        "kind": "text",
                        "image_orientation": "auto",
                    },
                },
                {
                    "slide_no": 2,
                    "goal": "Adoption Snapshot",
                    "include_in_contents": True,
                    "context": {
                        "metrics": [
                            {"label": "Templates profiled", "value": 12},
                            {"label": "Decks generated", "value": 24},
                        ]
                    },
                    "layout_request": {
                        "kind": "metrics",
                        "image_orientation": "auto",
                    },
                },
                {
                    "slide_no": 3,
                    "goal": "Why It Matters",
                    "include_in_contents": True,
                    "context": {
                        "summary": "Pair context with an uploaded image.",
                        "caption": "Workflow preview",
                    },
                    "assets": {
                        "images": [
                            {"ref": "image_1", "fit": "contain"},
                        ]
                    },
                    "layout_request": {
                        "kind": "text_image",
                        "image_orientation": "auto",
                    },
                },
            ],
        }
    }


class ValidatorTestCase(unittest.TestCase):
    """Verify template-contract, authoring, and runtime payload validation."""

    def test_validate_template_contract_accepts_built_in_contract(self) -> None:
        contract = validate_template_contract(get_built_in_contract().to_dict())

        self.assertIsInstance(contract, TemplateContract)
        self.assertEqual(contract.template_id, "autoreport-editorial-v1")
        self.assertEqual(
            [pattern.pattern_id for pattern in contract.slide_patterns],
            [
                "text.editorial",
                "metrics.editorial",
                "text_image.editorial",
                "text_image.editorial.two_horizontal",
                "text_image.editorial.two_vertical",
                "text_image.editorial.three_horizontal",
                "text_image.editorial.three_vertical",
            ],
        )
        self.assertEqual(
            [
                (
                    pattern.pattern_id,
                    pattern.image_count,
                    pattern.image_layout,
                    pattern.caption_slots,
                    pattern.body_slot_count,
                )
                for pattern in contract.slide_patterns
                if pattern.kind == "text_image"
            ],
            [
                ("text_image.editorial", 1, "stack", 1, 1),
                ("text_image.editorial.two_horizontal", 2, "horizontal", 1, 1),
                ("text_image.editorial.two_vertical", 2, "vertical", 1, 1),
                ("text_image.editorial.three_horizontal", 3, "horizontal", 1, 1),
                ("text_image.editorial.three_vertical", 3, "vertical", 1, 1),
            ],
        )

    def test_validate_payload_accepts_editorial_text_and_metrics_payload(self) -> None:
        payload = validate_payload(
            build_valid_payload(),
            get_built_in_contract(),
        )

        self.assertIsInstance(payload, ReportPayload)
        self.assertEqual(payload.template_id, "autoreport-editorial-v1")
        self.assertEqual([slide.kind for slide in payload.slides], ["text", "metrics"])
        self.assertEqual(
            [slide.pattern_id for slide in payload.slides],
            ["text.editorial", "metrics.editorial"],
        )

    def test_validate_payload_accepts_multi_image_runtime_payload(self) -> None:
        payload = validate_payload(
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
                            "title": "Two Images",
                            "include_in_contents": True,
                            "body": ["Compare two screenshots side by side."],
                            "pattern_id": "text_image.editorial.two_horizontal",
                            "slot_overrides": {
                                "text_image.image_1": {
                                    "image": {"ref": "image_1", "fit": "contain"}
                                },
                                "text_image.image_2": {
                                    "image": {"ref": "image_2", "fit": "contain"}
                                },
                                "text_image.caption_1": {
                                    "text": "Shared caption"
                                },
                            },
                        }
                    ],
                }
            },
            get_built_in_contract(),
            available_image_refs=("image_1", "image_2"),
        )

        self.assertEqual(payload.slides[0].pattern_id, "text_image.editorial.two_horizontal")
        self.assertEqual(len(payload.slides[0].slot_overrides), 3)
        self.assertIsNone(payload.slides[0].image)

    def test_validate_authoring_payload_accepts_authoring_contract(self) -> None:
        payload = validate_authoring_payload(
            build_valid_authoring_payload(),
            get_built_in_contract(),
            available_image_refs=("image_1",),
        )

        self.assertIsInstance(payload, AuthoringPayload)
        self.assertEqual(payload.template_id, "autoreport-editorial-v1")
        self.assertEqual([slide.goal for slide in payload.slides], ["What It Does", "Adoption Snapshot", "Why It Matters"])
        self.assertEqual(payload.slides[-1].layout_request.image_orientation, "auto")

    def test_validate_authoring_payload_rejects_missing_layout_request(self) -> None:
        payload = build_valid_authoring_payload()
        del payload["authoring_payload"]["slides"][0]["layout_request"]

        with self.assertRaises(ValidationError) as context:
            validate_authoring_payload(
                payload,
                get_built_in_contract(),
                available_image_refs=("image_1",),
            )

        self.assertIn(
            "Field 'slides[0].layout_request' is required.",
            context.exception.errors,
        )

    def test_validate_authoring_payload_rejects_mismatched_image_count(self) -> None:
        payload = build_valid_authoring_payload()
        payload["authoring_payload"]["slides"][2]["layout_request"]["image_count"] = 2

        with self.assertRaises(ValidationError) as context:
            validate_authoring_payload(
                payload,
                get_built_in_contract(),
                available_image_refs=("image_1",),
            )

        self.assertIn(
            "Field 'slides[2].layout_request.image_count' must match the number of provided images.",
            context.exception.errors,
        )

    def test_validate_authoring_payload_rejects_unsupported_orientation(self) -> None:
        payload = build_valid_authoring_payload()
        payload["authoring_payload"]["slides"][2]["layout_request"]["image_orientation"] = "diagonal"

        with self.assertRaises(ValidationError) as context:
            validate_authoring_payload(
                payload,
                get_built_in_contract(),
                available_image_refs=("image_1",),
            )

        self.assertIn(
            "Field 'slides[2].layout_request.image_orientation' must be one of 'auto', 'horizontal', 'vertical', or 'stack'.",
            context.exception.errors,
        )

    def test_validate_authoring_payload_rejects_missing_pattern_match(self) -> None:
        payload = build_valid_authoring_payload()
        payload["authoring_payload"]["slides"][2]["assets"]["images"].append(
            {"ref": "image_2", "fit": "contain"}
        )
        payload["authoring_payload"]["slides"][2]["assets"]["images"].append(
            {"ref": "image_3", "fit": "contain"}
        )
        payload["authoring_payload"]["slides"][2]["layout_request"]["image_count"] = 3
        payload["authoring_payload"]["slides"][2]["layout_request"]["image_orientation"] = "horizontal"

        validated = validate_authoring_payload(
            payload,
            get_built_in_contract(),
            available_image_refs=("image_1", "image_2", "image_3"),
        )
        self.assertEqual(
            validated.slides[2].layout_request.image_orientation,
            "horizontal",
        )

        payload["authoring_payload"]["slides"][2]["layout_request"]["image_orientation"] = "stack"
        with self.assertRaises(ValidationError) as context:
            validate_authoring_payload(
                payload,
                get_built_in_contract(),
                available_image_refs=("image_1", "image_2", "image_3"),
            )

        self.assertIn(
            "Field 'slides[2].layout_request' does not match any pattern in template 'autoreport-editorial-v1' for kind 'text_image', image_count=3, image_orientation='stack'.",
            context.exception.errors,
        )

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


if __name__ == "__main__":
    unittest.main()
