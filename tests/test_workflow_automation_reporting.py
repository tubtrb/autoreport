"""Tests for the v0.4 workflow automation orchestration reporting adapter."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path


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

from experiments.v04.prototypes.workflow_automation_reporting import (
    finalize_workflow_automation_run,
)
from experiments.v04.prototypes.workflow_automation_sandbox import (
    run_workflow_automation_sandbox,
)
from autoreport.validator import ValidationError


def build_repo_root() -> Path:
    return Path(tempfile.mkdtemp()) / "autoreport_v0.4-incubator2"


def write_sandbox_inputs(
    *,
    sandbox_root: Path,
    include_human_review: bool,
    image_ref: str = "image_1",
) -> None:
    (sandbox_root / "inputs").mkdir(parents=True, exist_ok=True)
    (sandbox_root / "inputs" / "run-config.yaml").write_text(
        "\n".join(
            [
                "trigger:",
                "  name: temp-demo-run",
                "  source: reporting-test",
                "  cadence: on_demand",
                "built_in: autoreport_editorial",
                "plan_options:",
                "  include_text_shaping: false",
                f"  include_human_review: {'true' if include_human_review else 'false'}",
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
                "  title: Autoreport Reporting",
                "  subtitle:",
                "    - Workflow automation reporting adapter",
                "slides:",
                "  - kind: text",
                "    title: Reporting Goal",
                "    include_in_contents: true",
                "    body:",
                "      - Emit .codex orchestration records without changing runtime entrypoints.",
                "  - kind: text_image",
                "    title: Why It Matters",
                "    include_in_contents: true",
                "    body:",
                "      - The adapter should surface artifacts and remaining review work.",
                "    image:",
                f"      ref: {image_ref}",
                "      fit: contain",
                "    caption: Reporting preview.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


class WorkflowAutomationReportingTestCase(unittest.TestCase):
    """Verify status/final report compatibility for v0.4 sandbox runs."""

    def test_successful_run_without_review_writes_in_progress_status(self) -> None:
        repo_root = build_repo_root()
        sandbox_root = repo_root / "experiments" / "v04" / "sandboxes" / "no-review-run"
        try:
            write_sandbox_inputs(
                sandbox_root=sandbox_root,
                include_human_review=False,
            )

            run_workflow_automation_sandbox(
                sandbox_root,
                repo_root=repo_root,
            )

            status_path = repo_root / ".codex" / "worker-status.json"
            status_payload = json.loads(status_path.read_text(encoding="utf-8"))
            status_report = collect_worker_reports.collect_status_report(
                status_path,
                timedelta(hours=12),
            )
        finally:
            shutil.rmtree(repo_root.parent, ignore_errors=True)

        self.assertEqual(status_payload["status"], "in_progress")
        self.assertEqual(status_report["errors"], [])
        self.assertTrue(status_report["artifact_paths"])

    def test_blocked_run_writes_collector_compatible_status(self) -> None:
        repo_root = build_repo_root()
        sandbox_root = repo_root / "experiments" / "v04" / "sandboxes" / "blocked-run"
        try:
            write_sandbox_inputs(
                sandbox_root=sandbox_root,
                include_human_review=True,
                image_ref="missing_image_ref",
            )

            with self.assertRaises(ValidationError):
                run_workflow_automation_sandbox(
                    sandbox_root,
                    repo_root=repo_root,
                )

            status_path = repo_root / ".codex" / "worker-status.json"
            status_payload = json.loads(status_path.read_text(encoding="utf-8"))
            status_report = collect_worker_reports.collect_status_report(
                status_path,
                timedelta(hours=12),
            )
        finally:
            shutil.rmtree(repo_root.parent, ignore_errors=True)

        self.assertEqual(status_payload["status"], "blocked")
        self.assertEqual(status_report["errors"], [])
        self.assertIn("remaining_gap", status_payload["evidence"])
        self.assertTrue(status_payload["evidence"]["remaining_gap"])

    def test_finalize_writes_valid_worker_final_record(self) -> None:
        repo_root = build_repo_root()
        sandbox_root = repo_root / "experiments" / "v04" / "sandboxes" / "finalize-run"
        try:
            write_sandbox_inputs(
                sandbox_root=sandbox_root,
                include_human_review=True,
            )

            run_workflow_automation_sandbox(
                sandbox_root,
                repo_root=repo_root,
            )
            final_path = finalize_workflow_automation_run(
                sandbox_root=sandbox_root,
                completion_summary="Workflow automation reporting adapter is ready for master review.",
                known_gaps="Human approval was recorded in sandbox review notes only.",
                repo_root=repo_root,
            )
            final_payload = json.loads(final_path.read_text(encoding="utf-8"))
            final_report = collect_worker_reports.collect_final_report(final_path)
        finally:
            shutil.rmtree(repo_root.parent, ignore_errors=True)

        self.assertEqual(final_report["errors"], [])
        self.assertTrue(final_report["ready_for_review"])
        self.assertTrue(final_report["primary_artifact_exists"])
        self.assertTrue(final_payload["ready_for_master_review"])
        self.assertIn(
            final_payload["primary_artifact_path"],
            final_payload["artifact_paths"],
        )


if __name__ == "__main__":
    unittest.main()
