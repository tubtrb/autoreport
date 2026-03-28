"""Tests for the public FastAPI contract-first demo application."""

from __future__ import annotations

import base64
from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pptx import Presentation

from autoreport.web.app import MEDIA_TYPE_PPTX, app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)

VALID_PAYLOAD_YAML = """
report_payload:
  payload_version: autoreport.payload.v1
  template_id: autoreport-editorial-v1
  title_slide:
    title: Autoreport
    subtitle:
      - Template-aware PPTX autofill engine
  contents:
    enabled: true
  slides:
    - kind: text
      title: What It Does
      include_in_contents: true
      body:
        - Generate editable PowerPoint decks from structured inputs.
      slot_overrides: {}
    - kind: metrics
      title: Adoption Snapshot
      include_in_contents: true
      items:
        - label: Templates profiled
          value: 12
      slot_overrides: {}
""".strip()

VALID_TEXT_IMAGE_PAYLOAD_YAML = """
report_payload:
  payload_version: autoreport.payload.v1
  template_id: autoreport-editorial-v1
  title_slide:
    title: Autoreport
    subtitle:
      - Template-aware PPTX autofill engine
  contents:
    enabled: true
  slides:
    - kind: text_image
      title: Why It Matters
      include_in_contents: true
      body:
        - Teams keep their own template language.
      image:
        ref: image_1
        fit: contain
      caption: Workflow preview
      slot_overrides: {}
""".strip()


class WebAppTestCase(unittest.TestCase):
    """Verify the demo page and generation API behavior."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_renders_contract_payload_and_upload_panels(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Inspect the contract, fill the payload", response.text)
        self.assertIn("Template Contract", response.text)
        self.assertIn("Report Payload", response.text)
        self.assertIn("Image Uploads", response.text)
        self.assertIn("Load Image Example", response.text)
        self.assertIn("Insert Text Slide", response.text)
        self.assertIn("Insert Metrics Slide", response.text)
        self.assertIn("Insert Text + Image Slide", response.text)
        self.assertIn("Current Deck Summary", response.text)
        self.assertIn("This is the template's capability map.", response.text)
        self.assertIn("image_1", response.text)
        self.assertIn("built-in editorial template", response.text)

    def test_healthcheck_returns_ok(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_generate_endpoint_returns_pptx_attachment(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_PAYLOAD_YAML,
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
        self.assertEqual(len(presentation.slides), 4)

    def test_generate_endpoint_binds_uploaded_image_refs(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": VALID_TEXT_IMAGE_PAYLOAD_YAML,
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

    def test_generate_endpoint_returns_parse_errors(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={"payload_yaml": "report_payload: [broken", "image_manifest": "[]"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_type"], "yaml_parse_error")
        self.assertIn("Failed to parse YAML:", response.json()["message"])

    def test_generate_endpoint_returns_validation_errors(self) -> None:
        response = self.client.post(
            "/api/generate",
            data={
                "payload_yaml": """
report_payload:
  payload_version: autoreport.payload.v1
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
                data={"payload_yaml": VALID_PAYLOAD_YAML, "image_manifest": "[]"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_type"], "internal_error")
        self.assertEqual(
            response.json()["message"],
            "An unexpected internal error occurred.",
        )


if __name__ == "__main__":
    unittest.main()
