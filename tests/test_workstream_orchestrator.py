from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "codex" / "skills" / "workstream-orchestrator" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cleanup_retired_worktrees  # noqa: E402
import collect_worker_reports  # noqa: E402
import sync_policy_worktrees  # noqa: E402
import workstream_runtime  # noqa: E402


class WorkstreamRuntimeTests(unittest.TestCase):
    def test_parse_worktree_list_handles_porcelain_output(self) -> None:
        text = (
            "worktree C:/repo\n"
            "HEAD abc123\n"
            "branch refs/heads/codex/v0.3-web-authoring-ux\n\n"
            "worktree C:/repo2\n"
            "HEAD def456\n"
            "branch refs/heads/codex/v0.3-master\n"
        )
        entries = workstream_runtime.parse_worktree_list(text)
        self.assertEqual(2, len(entries))
        self.assertEqual("C:/repo", entries[0]["worktree"])
        self.assertEqual("refs/heads/codex/v0.3-master", entries[1]["branch"])

    def test_discover_workstreams_uses_local_config_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_root = Path(tmp) / "autoreport_v0.3-web-authoring-ux"
            codex_dir = task_root / ".codex"
            codex_dir.mkdir(parents=True)
            (codex_dir / "workstream.json").write_text(
                json.dumps(
                    {
                        "key": "ux",
                        "test_modules": ["tests.test_web_app"],
                        "orchestration_enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            fake_output = (
                f"worktree {task_root}\n"
                "HEAD abc123\n"
                "branch refs/heads/codex/v0.3-web-authoring-ux\n\n"
                f"worktree {Path(tmp) / 'autoreport'}\n"
                "HEAD def456\n"
                "branch refs/heads/codex/v0.3-master\n"
            )
            fake_completed = mock.Mock(returncode=0, stdout=fake_output, stderr="")
            with mock.patch.object(workstream_runtime, "run_git", return_value=fake_completed):
                workstreams = workstream_runtime.discover_workstreams()
            self.assertEqual(1, len(workstreams))
            self.assertEqual("ux", workstreams[0].key)
            self.assertEqual(("tests.test_web_app",), workstreams[0].test_modules)

    def test_discover_retired_sibling_directories_ignores_registered_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            active = (workspace_root / "autoreport_v0.3-web-authoring-ux").resolve()
            retired = (workspace_root / "autoreport_v0.3-old-branch").resolve()
            unrelated = (workspace_root / "something_else").resolve()
            active.mkdir()
            retired.mkdir()
            unrelated.mkdir()
            with mock.patch.object(workstream_runtime, "WORKSPACE_ROOT", workspace_root), mock.patch.object(
                workstream_runtime, "registered_worktree_paths", return_value={active}
            ):
                retired_dirs = workstream_runtime.discover_retired_sibling_directories()
            self.assertEqual([retired], retired_dirs)

    def test_shared_broadcast_policy_is_present_in_bootstrap_docs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
        autoreport_skill_text = (
            repo_root / "codex" / "skills" / "autoreport-dev" / "SKILL.md"
        ).read_text(encoding="utf-8")
        orchestrator_skill_text = (
            repo_root / "codex" / "skills" / "workstream-orchestrator" / "SKILL.md"
        ).read_text(encoding="utf-8")
        orchestration_ref_text = (
            repo_root
            / "codex"
            / "skills"
            / "workstream-orchestrator"
            / "references"
            / "orchestration.md"
        ).read_text(encoding="utf-8")

        self.assertIn("only authoritative branch-specific instruction channel", agents_text)
        self.assertIn("do not restate branch-specific tasks", agents_text)
        self.assertIn("shared broadcast", autoreport_skill_text)
        self.assertIn("must\n  be a single shared reminder", orchestrator_skill_text)
        self.assertIn("must\n  not regenerate or paraphrase branch-specific instructions", orchestration_ref_text)

    def test_stale_code_cleanup_policy_is_present_in_bootstrap_docs(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
        autoreport_skill_text = (
            repo_root / "codex" / "skills" / "autoreport-dev" / "SKILL.md"
        ).read_text(encoding="utf-8")
        orchestrator_skill_text = (
            repo_root / "codex" / "skills" / "workstream-orchestrator" / "SKILL.md"
        ).read_text(encoding="utf-8")
        orchestration_ref_text = (
            repo_root
            / "codex"
            / "skills"
            / "workstream-orchestrator"
            / "references"
            / "orchestration.md"
        ).read_text(encoding="utf-8")

        self.assertIn("stale code", agents_text)
        self.assertIn("Do not keep \"old but maybe useful later\" tracked code", agents_text)
        self.assertIn("remove the stale predecessor path in the same task", autoreport_skill_text)
        self.assertIn("stale predecessor code", orchestrator_skill_text)
        self.assertIn("Treat stale tracked code", orchestration_ref_text)

    def test_report_example_templates_cover_required_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        status_template = json.loads(
            (
                repo_root
                / "codex"
                / "skills"
                / "workstream-orchestrator"
                / "references"
                / "worker-status.example.json"
            ).read_text(encoding="utf-8")
        )
        final_template = json.loads(
            (
                repo_root
                / "codex"
                / "skills"
                / "workstream-orchestrator"
                / "references"
                / "worker-final.example.json"
            ).read_text(encoding="utf-8")
        )

        self.assertTrue(set(collect_worker_reports.STATUS_REQUIRED_FIELDS).issubset(status_template))
        self.assertIn("evidence", status_template)
        self.assertTrue(
            set(collect_worker_reports.STATUS_EVIDENCE_REQUIRED_FIELDS).issubset(
                status_template["evidence"]
            )
        )
        self.assertTrue(set(collect_worker_reports.FINAL_REQUIRED_FIELDS).issubset(final_template))


class CollectorContractTests(unittest.TestCase):
    def test_collect_status_report_rejects_empty_required_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "worker-status.json"
            path.write_text(
                json.dumps(
                    {
                        "workstream_key": "generation-preview",
                        "branch": "codex/v0.3-generation-preview",
                        "head": "abc123",
                        "updated_at": "2026-03-29T01:00:00+09:00",
                        "status": "in_progress",
                        "task_summary": "",
                        "last_green_test_command": "",
                        "working_tree_clean": False,
                        "evidence": {
                            "input": "",
                            "command": "",
                            "artifact_paths": [],
                            "visible_result": "",
                            "remaining_gap": "",
                        },
                        "sync_notes": "",
                    }
                ),
                encoding="utf-8",
            )
            report = collect_worker_reports.collect_status_report(path, timedelta(hours=12))

        fields = {item["field"] for item in report["errors"]}
        self.assertIn("task_summary", fields)
        self.assertIn("last_green_test_command", fields)
        self.assertIn("evidence.input", fields)
        self.assertIn("evidence.command", fields)
        self.assertIn("evidence.artifact_paths", fields)
        self.assertIn("sync_notes", fields)

    def test_collect_final_report_rejects_empty_required_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "worker-final.json"
            path.write_text(
                json.dumps(
                    {
                        "workstream_key": "release-prep",
                        "branch": "codex/v0.3-release-prep",
                        "head": "abc123",
                        "completed_at": "",
                        "completion_summary": "",
                        "last_green_test_command": "",
                        "primary_artifact_path": "",
                        "artifact_paths": [],
                        "visible_result": "",
                        "known_gaps": "",
                        "ready_for_master_review": True,
                    }
                ),
                encoding="utf-8",
            )
            report = collect_worker_reports.collect_final_report(path)

        fields = {item["field"] for item in report["errors"]}
        self.assertIn("completed_at", fields)
        self.assertIn("completion_summary", fields)
        self.assertIn("last_green_test_command", fields)
        self.assertIn("primary_artifact_path", fields)
        self.assertIn("artifact_paths", fields)
        self.assertIn("visible_result", fields)
        self.assertIn("known_gaps", fields)

    def test_filter_workstreams_by_key_reports_missing_keys(self) -> None:
        workstreams = [
            workstream_runtime.Workstream(
                key="generation-preview",
                branch="codex/v0.3-generation-preview",
                path=Path("C:/fake/generation-preview"),
                test_modules=("tests.test_generator",),
            ),
            workstream_runtime.Workstream(
                key="release-prep",
                branch="codex/v0.3-release-prep",
                path=Path("C:/fake/release-prep"),
                test_modules=("tests.test_cli",),
            ),
        ]

        selected, missing = collect_worker_reports.filter_workstreams_by_key(
            workstreams,
            ["release-prep", "unknown-key"],
        )

        self.assertEqual(["release-prep"], [item.key for item in selected])
        self.assertEqual(["unknown-key"], missing)


class CleanupRetiredWorktreesTests(unittest.TestCase):
    def test_delete_candidates_blocks_nonempty_without_flag(self) -> None:
        records = [
            {"path": "C:/tmp/empty", "item_count": 0, "empty": True},
            {"path": "C:/tmp/nonempty", "item_count": 2, "empty": False},
        ]
        with mock.patch.object(cleanup_retired_worktrees, "delete_directory") as delete_directory:
            deleted, blocked = cleanup_retired_worktrees.delete_candidates(records, allow_nonempty=False)
        self.assertEqual(1, len(deleted))
        self.assertEqual(1, len(blocked))
        delete_directory.assert_called_once_with(Path("C:/tmp/empty"))

    def test_delete_candidates_reports_delete_error_as_blocker(self) -> None:
        records = [{"path": "C:/tmp/locked", "item_count": 0, "empty": True}]
        with mock.patch.object(cleanup_retired_worktrees, "delete_directory", side_effect=PermissionError("locked")):
            deleted, blocked = cleanup_retired_worktrees.delete_candidates(records, allow_nonempty=False)
        self.assertEqual([], deleted)
        self.assertEqual(1, len(blocked))
        self.assertIn("Deletion failed", blocked[0]["reason"])


class SyncPolicyWorktreesTests(unittest.TestCase):
    def make_workstream(self) -> workstream_runtime.Workstream:
        return workstream_runtime.Workstream(
            key="generation-preview",
            branch="codex/v0.3-generation-preview",
            path=Path("C:/fake/worktree"),
            test_modules=("tests.test_generator",),
        )

    def test_sync_workstream_refuses_dirty_without_checkpoint(self) -> None:
        workstream = self.make_workstream()
        with mock.patch.object(sync_policy_worktrees, "ensure_on_branch"), mock.patch.object(
            sync_policy_worktrees, "worktree_is_dirty", return_value=True
        ):
            result = sync_policy_worktrees.sync_workstream(
                workstream,
                base_branch="codex/v0.3-master",
                checkpoint_dirty=False,
                push=False,
                dry_run=True,
            )
        self.assertIn("Dirty worktree requires --checkpoint-dirty", result["errors"][0])

    def test_sync_workstream_skips_push_when_no_remote_and_no_unique_commits(self) -> None:
        workstream = self.make_workstream()
        with mock.patch.object(sync_policy_worktrees, "ensure_on_branch"), mock.patch.object(
            sync_policy_worktrees, "worktree_is_dirty", return_value=False
        ), mock.patch.object(
            sync_policy_worktrees, "branch_unique_commit_count", return_value=0
        ), mock.patch.object(
            sync_policy_worktrees, "run_narrow_tests", return_value={"command": "", "ok": True, "exit_code": 0, "stdout": "", "stderr": ""}
        ), mock.patch.object(
            sync_policy_worktrees, "branch_has_remote", return_value=False
        ):
            result = sync_policy_worktrees.sync_workstream(
                workstream,
                base_branch="codex/v0.3-master",
                checkpoint_dirty=False,
                push=True,
                dry_run=True,
            )
        self.assertTrue(result["ok"])
        self.assertTrue(result["push"]["skipped"])

    def test_push_branch_uses_force_with_lease_for_existing_remote(self) -> None:
        workstream = self.make_workstream()
        with mock.patch.object(sync_policy_worktrees, "branch_has_remote", return_value=True):
            result = sync_policy_worktrees.push_branch(workstream, dry_run=True)
        self.assertEqual("git push --force-with-lease", result["command"])


if __name__ == "__main__":
    unittest.main()
