"""Tests for the public FastAPI demo application."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from autoreport.web.app import MEDIA_TYPE_PPTX, app


VALID_REPORT_YAML = """
title: Weekly Report
team: Platform Team
week: 2026-W24
highlights:
  - Built the generation pipeline.
metrics:
  tasks_completed: 8
  open_issues: 3
risks:
  - Layout polish is still pending.
next_steps:
  - Review the generated deck.
""".strip()


class WebAppTestCase(unittest.TestCase):
    """Verify the demo page and generation API behavior."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_page_renders_expected_controls(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("YAML을 붙여 넣고 바로 PPTX를 받아보세요.", response.text)
        self.assertIn("예제 불러오기", response.text)
        self.assertIn("현재 상태", response.text)
        self.assertIn("Autoreport 공개 데모", response.text)

    def test_healthcheck_returns_ok(self) -> None:
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_generate_endpoint_returns_pptx_attachment(self) -> None:
        response = self.client.post(
            "/api/generate",
            json={"report_yaml": VALID_REPORT_YAML},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], MEDIA_TYPE_PPTX)
        self.assertIn(
            'attachment; filename="weekly_report.pptx"',
            response.headers["content-disposition"],
        )
        self.assertGreater(len(response.content), 0)

    def test_generate_endpoint_returns_parse_errors(self) -> None:
        response = self.client.post(
            "/api/generate",
            json={"report_yaml": "title: [broken"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_type"], "yaml_parse_error")
        self.assertIn("Failed to parse YAML:", response.json()["message"])

    def test_generate_endpoint_returns_validation_errors(self) -> None:
        response = self.client.post(
            "/api/generate",
            json={
                "report_yaml": """
title: "  "
team: Platform Team
week: 2026-W24
highlights: []
metrics:
  tasks_completed: -1
risks:
  - Risk item
next_steps:
  - Next step
""".strip()
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_type"], "validation_error")
        self.assertEqual(response.json()["message"], "Report validation failed.")
        self.assertIn(
            "Field 'title' must be a non-empty string.",
            response.json()["errors"],
        )

    def test_generate_endpoint_returns_generic_internal_errors(self) -> None:
        with patch(
            "autoreport.web.app.generate_report_from_mapping",
            side_effect=RuntimeError("boom"),
        ):
            response = self.client.post(
                "/api/generate",
                json={"report_yaml": VALID_REPORT_YAML},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error_type"], "internal_error")
        self.assertEqual(
            response.json()["message"],
            "An unexpected internal error occurred.",
        )
