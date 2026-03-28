"""Tests for the public FastAPI contract-first demo application."""

from __future__ import annotations

import base64
from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pptx import Presentation

from autoreport.web.app import MEDIA_TYPE_PPTX, WEBSITE_INTRO_EXAMPLE_YAML, app


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

VALID_REPORT_CONTENT_WITH_DESCRIPTIVE_IMAGE_YAML = """
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
        image_1: Middle East strategic map infographic
        caption_1: Example caption
""".strip()

VALID_REPORT_CONTENT_WITH_TWO_DESCRIPTIVE_IMAGES_YAML = """
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
        title: First visual
        body_1: |
          First description.
        image_1: First draft image note
        caption_1: First caption
    - pattern_id: text_image.editorial
      slots:
        title: Second visual
        body_1: |
          Second description.
        image_1: Second draft image note
        caption_1: Second caption
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


class WebAppTestCase(unittest.TestCase):
    """Verify the demo page, compile endpoint, and generation API behavior."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_renders_draft_first_homepage(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Draft the deck with AI", response.text)
        self.assertIn("AI Draft Input", response.text)
        self.assertIn("How To Use", response.text)
        self.assertIn("Advanced Debug: Compiled Report Payload", response.text)
        self.assertIn("Optional: View Template Contract", response.text)
        self.assertIn("Normalize Draft", response.text)
        self.assertIn("Copy AI Draft Prompt", response.text)
        self.assertIn("Copy AI Package", response.text)
        self.assertIn("Reset To AI Draft Prompt", response.text)
        self.assertIn("Load Website Intro Example", response.text)
        self.assertIn("authoring_payload", response.text)
        self.assertIn("report_content", response.text)
        self.assertIn("image_layout", response.text)
        self.assertIn("Do not declare the total slide count anywhere.", response.text)
        self.assertIn("The built-in editorial contract and AI draft prompt are loaded.", response.text)
        self.assertNotIn("Insert 2-Image Horizontal", response.text)
        self.assertNotIn("Workspace Actions", response.text)
        self.assertNotIn("AI Draft Guide", response.text)

    def test_demo_page_defaults_to_ai_draft_prompt(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("# Paste this brief into another AI and ask it to fill the report_content draft below.", response.text)
        self.assertIn("# 1. Return the final answer as one fenced ```yaml code block.", response.text)
        self.assertIn("# 3. Do not write any prose before or after the fenced YAML block.", response.text)
        self.assertIn("# - Each item in report_content.slides becomes one deck slide.", response.text)
        self.assertIn("# - In report_content, kind is optional when pattern_id already matches template_contract.", response.text)
        self.assertIn("# 8. Only use text_image patterns when the user explicitly wants a visual and can provide or upload a real image later.", response.text)
        self.assertIn("# 9. If no real image is available, do not add slots.image_* or caption_* fields. Use text.editorial or metrics.editorial instead.", response.text)
        self.assertIn("    - pattern_id: text.editorial\\n      slots:", response.text)
        self.assertNotIn("Describe the image the next AI should source or create.", response.text)

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

    def test_compile_endpoint_assigns_distinct_global_refs_to_multiple_descriptive_image_notes(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_WITH_TWO_DESCRIPTIVE_IMAGES_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        normalized = response.json()["normalized_authoring_yaml"]
        self.assertIn("ref: image_1", normalized)
        self.assertIn("ref: image_2", normalized)
        self.assertIn("Slide 1: image_1 was mapped to upload ref 'image_1'.", " ".join(response.json()["hints"]))
        self.assertIn("Slide 2: image_1 was mapped to upload ref 'image_2'.", " ".join(response.json()["hints"]))

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

    def test_generate_endpoint_binds_uploaded_image_refs(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_TEXT_IMAGE_AUTHORING_PAYLOAD_YAML,
                "image_manifest": '[{"ref":"image_1","field_name":"image_1","filename":"workflow.png"}]',
            },
            files={
                "image_1": ("workflow.png", PNG_BYTES, "image/png"),
            },
        )

        self.assertEqual(response.status_code, 200)
        presentation = Presentation(BytesIO(response.content))
        image_shapes = [
            shape
            for shape in presentation.slides[-1].shapes
            if hasattr(shape, "image")
        ]
        self.assertGreaterEqual(len(image_shapes), 1)

    def test_generate_endpoint_returns_friendly_missing_upload_error_for_report_content_image_notes(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_WITH_DESCRIPTIVE_IMAGE_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertEqual(response.json()["message"], "Payload validation failed.")
        self.assertTrue(
            any(
                "Slide 1 needs an uploaded image for ref 'image_1'." in item
                for item in response.json()["errors"]
            )
        )

    def test_generate_endpoint_returns_distinct_missing_upload_errors_for_multiple_descriptive_images(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_REPORT_CONTENT_WITH_TWO_DESCRIPTIVE_IMAGES_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 422)
        joined = " ".join(response.json()["errors"])
        self.assertIn("Slide 1 needs an uploaded image for ref 'image_1'.", joined)
        self.assertIn("Slide 2 needs an uploaded image for ref 'image_2'.", joined)

    def test_generate_endpoint_rejects_invalid_image_manifest_json(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_TEXT_IMAGE_AUTHORING_PAYLOAD_YAML,
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
