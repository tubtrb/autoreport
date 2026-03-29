"""Tests for the v0.4 workflow automation sandbox runner."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys
from datetime import timedelta

import yaml

SCRIPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "codex"
    / "skills"
    / "workstream-orchestrator"
    / "scripts"
)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collect_worker_reports  # noqa: E402

from experiments.v04.prototypes.workflow_automation_sandbox import (
    run_workflow_automation_sandbox,
)


REPO_SOURCE_ROOT = Path(__file__).resolve().parents[1]
MIXED_TEMPLATE_PATH = (
    REPO_SOURCE_ROOT
    / "experiments"
    / "v04"
    / "prototypes"
    / "pptxgenjs_template_spike"
    / "generated"
    / "v04-text-image-template.pptx"
)


class WorkflowAutomationSandboxTestCase(unittest.TestCase):
    """Verify the sandbox runner writes a full local rehearsal layout."""

    def test_runner_writes_contracts_drafts_review_and_artifact(self) -> None:
        repo_root = Path(tempfile.mkdtemp()) / "autoreport_v0.4-incubator2"
        sandbox_root = repo_root / "experiments" / "v04" / "sandboxes" / "demo-run"
        try:
            (sandbox_root / "inputs").mkdir(parents=True)
            (sandbox_root / "inputs" / "run-config.yaml").write_text(
                "\n".join(
                    [
                        "trigger:",
                        "  name: temp-demo-run",
                        "  source: test-suite",
                        "  cadence: on_demand",
                        "built_in: autoreport_editorial",
                        "plan_options:",
                        "  include_text_shaping: false",
                        "  include_human_review: true",
                        "  include_publish_handoff: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (sandbox_root / "inputs" / "report-brief.yaml").write_text(
                "\n".join(
                    [
                        "title_slide:",
                        "  title: Autoreport Sandbox",
                        "  subtitle:",
                        "    - Contract-first automation rehearsal",
                        "slides:",
                        "  - kind: text",
                        "    title: Migration Goal",
                        "    include_in_contents: true",
                        "    body:",
                        "      - Sandbox runner created the template contract and draft payload.",
                        "      - Human review remains explicit.",
                        "  - kind: metrics",
                        "    title: Current Snapshot",
                        "    include_in_contents: true",
                        "    items:",
                        "      - label: Tasks completed",
                        "        value: 2",
                        "      - label: Open issues",
                        "        value: 0",
                        "  - kind: text_image",
                        "    title: Why It Matters",
                        "    include_in_contents: true",
                        "    body:",
                        "      - The sandbox follows the current editorial payload shape.",
                        "    image:",
                        "      ref: image_1",
                        "      fit: contain",
                        "    caption: Sandbox image preview.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_workflow_automation_sandbox(
                sandbox_root,
                repo_root=repo_root,
            )

            contract_document = yaml.safe_load(
                (sandbox_root / "contracts" / "template-contract.yaml").read_text(
                    encoding="utf-8"
                )
            )
            payload_document = yaml.safe_load(
                (sandbox_root / "drafts" / "draft-report-payload.yaml").read_text(
                    encoding="utf-8"
                )
            )
            review_text = (sandbox_root / "reviews" / "review-notes.md").read_text(
                encoding="utf-8"
            )
            summary = json.loads(
                (sandbox_root / "logs" / "run-summary.json").read_text(
                    encoding="utf-8"
                )
            )
            workstream_config = json.loads(
                (repo_root / ".codex" / "workstream.json").read_text(
                    encoding="utf-8"
                )
            )
            status_path = repo_root / ".codex" / "worker-status.json"
            status_payload = json.loads(status_path.read_text(encoding="utf-8"))
            status_report = collect_worker_reports.collect_status_report(
                status_path,
                timedelta(hours=12),
            )
            artifact_exists = result.artifact_path.exists()
        finally:
            shutil.rmtree(repo_root.parent, ignore_errors=True)

        self.assertTrue(artifact_exists)
        self.assertEqual(
            contract_document["template_contract"]["template_id"],
            payload_document["report_payload"]["template_id"],
        )
        self.assertIn("Autoreport Sandbox", review_text)
        self.assertIn("Review generated deck", review_text)
        self.assertEqual(summary["template_name"], "autoreport_editorial")
        self.assertEqual(
            summary["slide_titles"],
            [
                "Autoreport Sandbox",
                "Contents",
                "Migration Goal",
                "Current Snapshot",
                "Why It Matters",
            ],
        )
        self.assertEqual(workstream_config["key"], "workflow-automation")
        self.assertEqual(
            workstream_config["test_modules"],
            [
                "tests.test_workflow_automation_spike",
                "tests.test_workflow_automation_sandbox",
                "tests.test_generator",
            ],
        )
        self.assertTrue(workstream_config["orchestration_enabled"])
        self.assertEqual(status_payload["status"], "ready_for_review")
        self.assertEqual(status_payload["workstream_key"], "workflow-automation")
        self.assertEqual(status_report["errors"], [])
        self.assertTrue(status_report["artifact_paths"])
        self.assertFalse((repo_root / ".codex" / "worker-final.json").exists())

    def test_runner_can_rehearse_against_a_mixed_user_template(self) -> None:
        repo_root = Path(tempfile.mkdtemp()) / "autoreport_v0.4-incubator2"
        sandbox_root = repo_root / "experiments" / "v04" / "sandboxes" / "mixed-run"
        try:
            (sandbox_root / "inputs").mkdir(parents=True)
            (sandbox_root / "inputs" / "run-config.yaml").write_text(
                "\n".join(
                    [
                        "trigger:",
                        "  name: temp-mixed-run",
                        "  source: test-suite",
                        "  cadence: on_demand",
                        "built_in: autoreport_editorial",
                        f"template_path: {MIXED_TEMPLATE_PATH}",
                        "plan_options:",
                        "  include_text_shaping: false",
                        "  include_human_review: true",
                        "  include_publish_handoff: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (sandbox_root / "inputs" / "report-brief.yaml").write_text(
                "\n".join(
                    [
                        "title_slide:",
                        "  title: Autoreport Mixed Sandbox",
                        "  subtitle:",
                        "    - User template mixed-layout rehearsal",
                        "slides:",
                        "  - kind: text_image",
                        "    title: Mixed Layout Check",
                        "    include_in_contents: true",
                        "    body:",
                        "      - The sandbox should route text and images into separate placeholders.",
                        "    image:",
                        "      ref: image_1",
                        "      fit: contain",
                        "    caption: Mixed template preview.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_workflow_automation_sandbox(
                sandbox_root,
                repo_root=repo_root,
            )

            summary = json.loads(
                (sandbox_root / "logs" / "run-summary.json").read_text(
                    encoding="utf-8"
                )
            )
            contract_document = json.loads(
                (sandbox_root / "contracts" / "template-contract.json").read_text(
                    encoding="utf-8"
                )
            )
            status_path = repo_root / ".codex" / "worker-status.json"
            status_report = collect_worker_reports.collect_status_report(
                status_path,
                timedelta(hours=12),
            )
            artifact_exists = result.artifact_path.exists()
        finally:
            shutil.rmtree(repo_root.parent, ignore_errors=True)

        self.assertTrue(artifact_exists)
        self.assertEqual(summary["template_name"], "v04-text-image-template")
        self.assertEqual(summary["template_reference"], str(MIXED_TEMPLATE_PATH.resolve()))
        self.assertEqual(
            [pattern["kind"] for pattern in contract_document["template_contract"]["slide_patterns"]],
            ["text", "metrics", "text_image"],
        )
        self.assertEqual(
            summary["slide_titles"],
            ["Autoreport Mixed Sandbox", "Contents", "Mixed Layout Check"],
        )
        self.assertEqual(status_report["errors"], [])


if __name__ == "__main__":
    unittest.main()
