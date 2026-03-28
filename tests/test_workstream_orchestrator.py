from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "codex" / "skills" / "workstream-orchestrator" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cleanup_retired_worktrees  # noqa: E402
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
