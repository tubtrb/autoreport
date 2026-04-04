"""Tests for the public FastAPI contract-first demo application."""

from __future__ import annotations

import base64
import gc
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import warnings

from fastapi.testclient import TestClient
from pptx import Presentation

from autoreport.web.app import (
    MANUAL_PROCEDURE_EXAMPLE_YAML,
    MEDIA_TYPE_PPTX,
    PROMPTED_MANUAL_PROCEDURE_EXAMPLE_YAML,
    PROMPTED_WEBSITE_INTRO_EXAMPLE_YAML,
    WEBSITE_INTRO_EXAMPLE_YAML,
    app,
)


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)

VALID_AUTHORING_PAYLOAD_YAML = """
authoring_payload:
  payload_version: autoreport.authoring.v1
  template_id: autoreport-editorial-v1
  deck_context:
    audience: executives
  title_slide:
    title: Autoreport
    subtitle:
      - Template-aware PPTX autofill engine
  contents:
    enabled: true
  slides:
    - slide_no: 1
      goal: What It Does
      include_in_contents: true
      context:
        summary: Generate editable PowerPoint decks from structured inputs.
      layout_request:
        kind: text
        image_orientation: auto
""".strip()

VALID_TEXT_IMAGE_AUTHORING_PAYLOAD_YAML = """
authoring_payload:
  payload_version: autoreport.authoring.v1
  template_id: autoreport-editorial-v1
  deck_context:
    audience: executives
  title_slide:
    title: Autoreport
    subtitle:
      - Template-aware PPTX autofill engine
  contents:
    enabled: true
  slides:
    - slide_no: 1
      goal: Visual Proof
      include_in_contents: true
      context:
        summary: Pair narrative context with an uploaded image.
        caption: Workflow preview
      assets:
        images:
          - ref: image_1
            fit: contain
      layout_request:
        kind: text_image
        image_orientation: auto
""".strip()

VALID_REPORT_CONTENT_WITH_IMAGE_YAML = """
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Autoreport
      subtitle_1: |
        Template-aware PPTX autofill engine
  slides:
    - pattern_id: text_image.editorial
      slots:
        title: Visual Proof
        body_1: |
          Explain what the visual should prove.
        image_1: image_1
        caption_1: Example caption
""".strip()

VALID_REPORT_CONTENT_YAML = """
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Autoreport
      subtitle_1: |
        Template-aware PPTX autofill engine
  contents_slide:
    pattern_id: contents.editorial
    slots:
      title: Contents
      body_1: |
        1. What It Does
  slides:
    - pattern_id: text.editorial
      slots:
        title: What It Does
        body_1: |
          Generate editable PowerPoint decks from structured inputs.
""".strip()

TRUNCATED_CLAUDE_REPORT_CONTENT_YAML = """
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Autoreport
      subtitle_1: |
        Template-aware PPTX autofill engine
  slides:
    - pattern_id: text_image.edito
""".strip()

MIXED_CHATGPT_STYLE_REPORT_CONTENT = """
report_content:
title_slide:
pattern_id: cover.editorial
slots:
title: 沃섎㈇????? ?겸뫖猷롦?餓λ쵎猷??類ㅺ쉭

```yaml
- pattern_id: text.editorial
  kind: text
  slots:
    title: 筌ㅼ뮄???袁㏃뻣?? ???뼎 ?怨몄젎
    body_1: |
      筌ㅼ뮄???겸뫖猷?? 癰귣벏鍮?怨몄몵嚥??袁㏃뻣??랁???덈뼄.
```
""".strip()

_SHORT_MANUAL_DETAIL_BODY = """        detail_body: |
          Review the starter YAML, note the built-in template mode, and confirm
          the page is ready before moving to the next step."""


def build_long_manual_procedure_example_yaml() -> str:
    replacement = "        detail_body: |\n" + "\n".join(
        [
            "          Review the starter YAML carefully and keep documenting each operator cue before moving forward."
            for _ in range(12)
        ]
    )
    return MANUAL_PROCEDURE_EXAMPLE_YAML.replace(
        _SHORT_MANUAL_DETAIL_BODY,
        replacement,
        1,
    )


class WebAppTestCase(unittest.TestCase):
    """Verify the public demo page and its public-only API contract."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_renders_text_first_homepage(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Edit the starter deck", response.text)
        self.assertIn("Starter Deck YAML", response.text)
        self.assertIn("Status", response.text)
        self.assertIn("Reset Starter Example", response.text)
        self.assertIn("Refresh Slide Assets", response.text)
        self.assertIn("Generate PPTX", response.text)
        self.assertIn("report_content", response.text)
        self.assertIn("text-first", response.text)
        self.assertIn("Keep public-web drafts to", response.text)
        self.assertIn("debug app or CLI", response.text)
        self.assertIn("Website Intro Starter", response.text)
        self.assertIn("Manual Procedure Starter", response.text)
        self.assertIn("PowerPoint Slide Preview", response.text)
        self.assertIn("matching upload panel on the", response.text)
        self.assertIn("list-style: none;", response.text)
        self.assertIn("font-size: 0.82rem;", response.text)
        self.assertNotIn("Image Order", response.text)
        self.assertNotIn("Screenshot Uploads", response.text)
        self.assertNotIn("Choose or paste screenshots for this slide", response.text)
        self.assertNotIn("Remove Upload", response.text)
        self.assertNotIn("Thumbnail Preview", response.text)
        self.assertNotIn("How To Use", response.text)
        self.assertNotIn("Image Uploads", response.text)
        self.assertNotIn("starter_app_workspace", response.text)
        self.assertNotIn("starter_app_uploads", response.text)
        self.assertNotIn("app-workspace.png", response.text)
        self.assertNotIn("/starter-assets/app-workspace.png", response.text)
        self.assertNotIn("Built-In", response.text)
        self.assertNotIn("Advanced Debug: Compiled Report Payload", response.text)
        self.assertNotIn("Optional: View Template Contract", response.text)
        self.assertNotIn("Normalize Draft", response.text)
        self.assertNotIn("Copy AI Package", response.text)
        self.assertNotIn("Optional: AI Prompt Package", response.text)
        self.assertNotIn("Reset To AI Draft Prompt", response.text)

    def test_demo_page_defaults_to_prompted_website_intro_starter(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Autoreport Website Quick Manual", response.text)
        self.assertIn("Published Guide And Updates Routes", response.text)
        self.assertIn("Edit The Starter Deck YAML", response.text)
        self.assertIn("Generate The Deck", response.text)
        self.assertIn("# Paste this brief into another AI", response.text)
        self.assertIn("report_content draft below", response.text)
        self.assertIn("User Guide `/guide/`", response.text)

    def test_healthcheck_returns_ok(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_compile_endpoint_returns_compiled_runtime_payload(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_AUTHORING_PAYLOAD_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload_kind"], "authoring")
        self.assertIn("report_payload:", response.json()["compiled_yaml"])
        self.assertIn("pattern_id: text.editorial", response.json()["compiled_yaml"])
        self.assertEqual(response.json()["slide_count"], 1)

    def test_compile_endpoint_normalizes_report_content_into_authoring_payload(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload_kind"], "content")
        self.assertIn("authoring_payload:", response.json()["normalized_authoring_yaml"])
        self.assertIn("goal: What It Does", response.json()["normalized_authoring_yaml"])
        self.assertIn("report_payload:", response.json()["compiled_yaml"])
        self.assertEqual(response.json()["required_images"], [])
        self.assertEqual(
            [preview["slide_title"] for preview in response.json()["slide_previews"]],
            ["Autoreport", "Contents", "What It Does"],
        )

    def test_compile_endpoint_accepts_report_content_without_kind(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("kind: text", response.json()["normalized_authoring_yaml"])

    def test_compile_endpoint_accepts_fenced_report_content(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": f"```yaml\n{VALID_REPORT_CONTENT_YAML}\n```",
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload_kind"], "content")
        self.assertIn("authoring_payload:", response.json()["normalized_authoring_yaml"])

    def test_compile_endpoint_returns_manual_required_image_order(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": MANUAL_PROCEDURE_EXAMPLE_YAML,
                "image_manifest": "[]",
                "built_in": "autoreport_manual",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload_kind"], "content")
        self.assertIn(
            "pattern_id: text_image.manual.procedure.three",
            response.json()["compiled_yaml"],
        )
        self.assertEqual(
            response.json()["required_images"],
            [
                {
                    "slide_no": 2,
                    "slide_title": "1.1 Review The Starter Example",
                    "alias": "image_1",
                    "ref": "image_1",
                },
                {
                    "slide_no": 3,
                    "slide_title": "1.2 Customize The Draft",
                    "alias": "image_1",
                    "ref": "image_2",
                },
                {
                    "slide_no": 3,
                    "slide_title": "1.2 Customize The Draft",
                    "alias": "image_2",
                    "ref": "image_3",
                },
                {
                    "slide_no": 4,
                    "slide_title": "1.3 Generate The PowerPoint",
                    "alias": "image_1",
                    "ref": "image_4",
                },
                {
                    "slide_no": 4,
                    "slide_title": "1.3 Generate The PowerPoint",
                    "alias": "image_2",
                    "ref": "image_5",
                },
                {
                    "slide_no": 4,
                    "slide_title": "1.3 Generate The PowerPoint",
                    "alias": "image_3",
                    "ref": "image_6",
                },
            ],
        )
        self.assertEqual(
            [preview["pattern_id"] for preview in response.json()["slide_previews"]],
            [
                "cover.manual",
                "contents.manual",
                "text.manual.section_break",
                "text_image.manual.procedure.one",
                "text_image.manual.procedure.two",
                "text_image.manual.procedure.three",
            ],
        )
        self.assertEqual(
            response.json()["slide_previews"][3]["image_blocks"],
            [
                {
                    "slot_name": "text_image.image_1",
                    "label": "image_1",
                    "ref": "image_1",
                    "fit": "contain",
                    "uploaded": False,
                    "x_pct": 66.4,
                    "y_pct": 21.4,
                    "w_pct": 26.0,
                    "h_pct": 40.8,
                }
            ],
        )

    def test_compile_endpoint_slide_previews_follow_runtime_continuation(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": build_long_manual_procedure_example_yaml(),
                "image_manifest": "[]",
                "built_in": "autoreport_manual",
            },
        )

        self.assertEqual(response.status_code, 200)
        continued_previews = [
            preview
            for preview in response.json()["slide_previews"]
            if preview["slide_title"].startswith("1.1 Review The Starter Example")
        ]
        self.assertGreaterEqual(len(continued_previews), 2)
        self.assertEqual(
            continued_previews[0]["slide_title"],
            "1.1 Review The Starter Example",
        )
        self.assertTrue(
            all(
                preview["slide_title"] == "1.1 Review The Starter Example (cont.)"
                for preview in continued_previews[1:]
            )
        )
        self.assertEqual(len(continued_previews[0]["image_blocks"]), 1)
        self.assertTrue(
            all(preview["image_blocks"] == [] for preview in continued_previews[1:])
        )
        self.assertIn("decorations", continued_previews[0])
        self.assertIn("font_size_pt", continued_previews[0]["text_blocks"][0])

    def test_compile_endpoint_rejects_image_backed_payloads_in_public_app(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_WITH_IMAGE_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertEqual(response.json()["message"], "Payload validation failed.")
        self.assertIn(
            "The public web demo currently supports text and metrics slides only.",
            response.json()["errors"],
        )

    def test_compile_endpoint_rejects_non_empty_image_manifest_in_public_app(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_YAML,
                "image_manifest": '[{"ref":"image_1","field_name":"image_1","filename":"workflow.png"}]',
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "The public web demo currently supports text and metrics slides only.",
            response.json()["errors"],
        )

    def test_compile_endpoint_rejects_mixed_partial_fence_ai_output(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": MIXED_CHATGPT_STYLE_REPORT_CONTENT,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_type"], "yaml_parse_error")
        self.assertIn("Mixed fenced and unfenced YAML content", response.json()["message"])

    def test_generate_endpoint_returns_clear_error_for_truncated_pattern_id(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": TRUNCATED_CLAUDE_REPORT_CONTENT_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "Field 'slides[0].slots' must be an object.",
            response.json()["errors"],
        )

    def test_generate_endpoint_returns_pptx_attachment_from_authoring_payload(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_AUTHORING_PAYLOAD_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], MEDIA_TYPE_PPTX)
        self.assertIn(
            'attachment; filename="autoreport_demo.pptx"',
            response.headers["content-disposition"],
        )
        presentation = Presentation(BytesIO(response.content))
        self.assertEqual(len(presentation.slides), 3)

    def test_generate_endpoint_accepts_report_content_draft(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        presentation = Presentation(BytesIO(response.content))
        self.assertEqual(len(presentation.slides), 3)

    def test_generate_endpoint_accepts_built_in_website_intro_example(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": WEBSITE_INTRO_EXAMPLE_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        presentation = Presentation(BytesIO(response.content))
        self.assertEqual(len(presentation.slides), 5)

    def test_generate_endpoint_accepts_prompted_built_in_website_intro_example(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": PROMPTED_WEBSITE_INTRO_EXAMPLE_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        presentation = Presentation(BytesIO(response.content))
        self.assertEqual(len(presentation.slides), 5)

    def test_generate_endpoint_accepts_manual_built_in_with_uploaded_images(self) -> None:
        manifest = [
            {
                "ref": f"image_{index}",
                "field_name": f"image_{index}",
                "filename": f"step_{index}.png",
            }
            for index in range(1, 7)
        ]
        files = [
            (f"image_{index}", (f"step_{index}.png", PNG_BYTES, "image/png"))
            for index in range(1, 7)
        ]
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": MANUAL_PROCEDURE_EXAMPLE_YAML,
                "image_manifest": json.dumps(manifest),
                "built_in": "autoreport_manual",
            },
            files=files,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], MEDIA_TYPE_PPTX)
        presentation = Presentation(BytesIO(response.content))
        self.assertEqual(len(presentation.slides), 6)

    def test_generate_endpoint_reports_missing_manual_uploads(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": PROMPTED_MANUAL_PROCEDURE_EXAMPLE_YAML,
                "image_manifest": "[]",
                "built_in": "autoreport_manual",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "Slide 2 needs an uploaded image for ref 'image_1'. Upload the matching file below before generating, or replace the draft image note with a real file path/ref.",
            response.json()["errors"],
        )

    def test_generate_endpoint_rejects_duplicate_manual_image_refs(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            response = self.client.post(
                "/api/generate",
                data={
                    "payload_yaml": MANUAL_PROCEDURE_EXAMPLE_YAML,
                    "image_manifest": json.dumps(
                        [
                            {
                                "ref": "image_1",
                                "field_name": "upload_1",
                                "filename": "one.png",
                            },
                            {
                                "ref": "image_1",
                                "field_name": "upload_2",
                                "filename": "two.png",
                            },
                        ]
                    ),
                    "built_in": "autoreport_manual",
                },
                files=[
                    ("upload_1", ("one.png", PNG_BYTES, "image/png")),
                    ("upload_2", ("two.png", PNG_BYTES, "image/png")),
                ],
            )
            gc.collect()

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "Field 'image_manifest[1].ref' must be unique.",
            response.json()["errors"],
        )
        resource_warnings = [
            warning
            for warning in caught
            if issubclass(warning.category, ResourceWarning)
        ]
        self.assertEqual(resource_warnings, [])

    def test_generate_endpoint_rejects_manual_upload_refs_with_path_separators(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": MANUAL_PROCEDURE_EXAMPLE_YAML,
                "image_manifest": json.dumps(
                    [
                        {
                            "ref": "../escape",
                            "field_name": "image_1",
                            "filename": "step_1.png",
                        },
                    ]
                ),
                "built_in": "autoreport_manual",
            },
            files=[("image_1", ("step_1.png", PNG_BYTES, "image/png"))],
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "Field 'image_manifest[0].ref' must not contain path separators.",
            response.json()["errors"],
        )

    def test_generate_endpoint_rejects_invalid_manual_upload_file_type(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": MANUAL_PROCEDURE_EXAMPLE_YAML,
                "image_manifest": json.dumps(
                    [
                        {
                            "ref": "image_1",
                            "field_name": "image_1",
                            "filename": "step_1.gif",
                        },
                    ]
                ),
                "built_in": "autoreport_manual",
            },
            files=[("image_1", ("step_1.gif", b"GIF89a", "image/gif"))],
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "Field 'image_manifest[0].ref' has an unsupported file type.",
            response.json()["errors"],
        )

    def test_generate_endpoint_rejects_image_backed_authoring_payload_in_public_app(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_TEXT_IMAGE_AUTHORING_PAYLOAD_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertIn(
            "The public web demo currently supports text and metrics slides only.",
            response.json()["errors"],
        )

    def test_generate_endpoint_rejects_invalid_image_manifest_json(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_YAML,
                "image_manifest": "[",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertEqual(response.json()["message"], "Payload validation failed.")
        self.assertIn(
            "Field 'image_manifest' must be a valid JSON list.",
            response.json()["errors"],
        )

    def test_generate_endpoint_returns_parse_errors(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={"payload_yaml": "authoring_payload: [broken", "image_manifest": "[]"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_type"], "yaml_parse_error")
        self.assertIn("Failed to parse YAML:", response.json()["message"])

    def test_generate_endpoint_cleans_temp_dir_after_parse_error_with_upload(self) -> None:
        leaked_temp_dir = Path(tempfile.mkdtemp(prefix="autoreport-web-test-"))
        with patch("autoreport.web.app.tempfile.mkdtemp", return_value=str(leaked_temp_dir)):
            response = self.client.post(
                "/api/generate",
                data={
                    "payload_yaml": "authoring_payload: [broken",
                    "image_manifest": json.dumps(
                        [
                            {
                                "ref": "image_1",
                                "field_name": "image_1",
                                "filename": "step_1.png",
                            },
                        ]
                    ),
                    "built_in": "autoreport_manual",
                },
                files=[("image_1", ("step_1.png", PNG_BYTES, "image/png"))],
            )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(leaked_temp_dir.exists())

    def test_generate_endpoint_returns_validation_errors(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": """
authoring_payload:
  payload_version: autoreport.authoring.v1
  template_id: autoreport-editorial-v1
  title_slide:
    title: "  "
    subtitle: []
  contents:
    enabled: true
  slides: []
""".strip(),
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertEqual(response.json()["message"], "Payload validation failed.")
        self.assertIn(
            "Field 'title_slide.title' must be a non-empty string.",
            response.json()["errors"],
        )

    def test_generate_endpoint_returns_generic_internal_errors(self) -> None:
        with patch(
            "autoreport.web.app.generate_report_from_mapping",
            side_effect=RuntimeError("boom"),
        ):
            response = self.client.post(
                "/api/generate",
                data={"payload_yaml": VALID_AUTHORING_PAYLOAD_YAML, "image_manifest": "[]"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_type"], "internal_error")
        self.assertEqual(
            response.json()["message"],
            "An unexpected internal error occurred.",
        )


if __name__ == "__main__":
    unittest.main()
