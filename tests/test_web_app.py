"""Tests for the public FastAPI contract-first demo application."""

from __future__ import annotations

from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pptx import Presentation

from autoreport.web.app import (
    MEDIA_TYPE_PPTX,
    PROMPTED_WEBSITE_INTRO_EXAMPLE_YAML,
    WEBSITE_INTRO_EXAMPLE_YAML,
    app,
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
title: 誘멸뎅-?대? 異⑸룎怨?以묐룞 ?뺤꽭

```yaml
- pattern_id: text.editorial
  kind: text
  slots:
    title: 理쒓렐 ?꾧컻? ?듭떖 ?곸젏
    body_1: |
      理쒓렐 異⑸룎? 蹂듯빀?곸쑝濡??꾧컻?섍퀬 ?덈떎.
```
""".strip()


class WebAppTestCase(unittest.TestCase):
    """Verify the public demo page and its public-only API contract."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_renders_text_first_homepage(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Edit the starter deck", response.text)
        self.assertIn("Starter Deck YAML", response.text)
        self.assertIn("How To Use", response.text)
        self.assertIn("Reset Starter Example", response.text)
        self.assertIn("Generate PPTX", response.text)
        self.assertIn("report_content", response.text)
        self.assertIn("text-first", response.text)
        self.assertIn("Keep public-web drafts to", response.text)
        self.assertIn("debug app or CLI", response.text)
        self.assertNotIn("Image Uploads", response.text)
        self.assertNotIn("Remove Upload", response.text)
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
        self.assertIn(
            "The main editor starts with AI prompt comments and the starter manual draft.",
            response.text,
        )
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
