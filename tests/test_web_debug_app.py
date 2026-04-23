"""Tests for the developer-facing Autoreport debug web app."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from autoreport.web.app import MANUAL_PROCEDURE_EXAMPLE_YAML
from autoreport.web.debug_app import app


VALID_REPORT_CONTENT_YAML = """
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Debug Deck
      subtitle_1: |
        Debug subtitle
  slides:
    - pattern_id: text.editorial
      kind: text
      slots:
        title: Debug slide
        body_1: |
          Debug content
""".strip()

VALID_TEXT_IMAGE_REPORT_CONTENT_YAML = """
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Debug Deck
      subtitle_1: |
        Debug subtitle
  slides:
    - pattern_id: text_image.editorial
      slots:
        title: Visual proof
        body_1: |
          Keep image-backed drafts available in the debug app.
        image_1: image_1
        caption_1: Debug caption
""".strip()


class WebDebugAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_debug_page_renders_debug_surface(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Autoreport Debug Demo", response.text)
        self.assertIn("Debug Workspace", response.text)
        self.assertIn("Repair Proof", response.text)
        self.assertIn("Debug Controls", response.text)
        self.assertIn("Normalized Authoring Payload", response.text)
        self.assertIn("Compiled Report Payload", response.text)
        self.assertIn("Load Starter Authoring", response.text)
        self.assertIn("Load AI Draft Prompt", response.text)

    def test_debug_page_embeds_full_ai_draft_prompt(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "# Complete the starter YAML below as the final answer.",
            response.text,
        )
        self.assertIn(
            "Goal: draft a screenshot-first procedure manual for Autoreport using the manual template.",
            response.text,
        )
        self.assertIn("Review The Starter Example", response.text)
        self.assertIn("Generate The PowerPoint", response.text)

    def test_debug_proof_page_renders_separate_proof_surface(self) -> None:
        response = self.client.get("/proof")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Autoreport Repair Proof", response.text)
        self.assertIn("Debug Workspace", response.text)
        self.assertIn("Repair Proof", response.text)
        self.assertIn("Proof Runbook", response.text)
        self.assertIn("Saved Corpus Recheck", response.text)
        self.assertIn("Live Server Smoke", response.text)
        self.assertIn("Stronger Live Proof", response.text)
        self.assertIn("run_manual_ai_regression.ps1", response.text)
        self.assertIn("run_server_proof.ps1", response.text)
        self.assertIn("recheck_manual_corpus.py", response.text)
        self.assertIn("record_visual_review.py", response.text)

    def test_debug_compile_route_is_wired(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={"payload_yaml": VALID_REPORT_CONTENT_YAML, "image_manifest": "[]"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload_kind"], "content")
        self.assertIn("report_payload:", response.json()["compiled_yaml"])

    def test_debug_compile_route_keeps_image_backed_drafts_available(self) -> None:
        response = self.client.post(
            "/api/compile",
            data={
                "payload_yaml": VALID_TEXT_IMAGE_REPORT_CONTENT_YAML,
                "image_manifest": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload_kind"], "content")
        self.assertIn("kind: text_image", response.json()["normalized_authoring_yaml"])
        self.assertIn("ref: image_1", response.json()["normalized_authoring_yaml"])

    def test_debug_compile_route_supports_manual_built_in_contract(self) -> None:
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
            "pattern_id: text.manual.section_break",
            response.json()["compiled_yaml"],
        )
        self.assertIn(
            "pattern_id: text_image.manual.procedure.three",
            response.json()["compiled_yaml"],
        )


if __name__ == "__main__":
    unittest.main()
