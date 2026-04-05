from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT
    / "codex"
    / "skills"
    / "branch-commit-guard"
    / "scripts"
    / "ensure_safe_branch.py"
)


class BranchCommitGuardScriptTests(unittest.TestCase):
    def run_guard(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

    def test_blocks_codex_next(self) -> None:
        result = self.run_guard("--branch", "codex/next")

        self.assertEqual(result.returncode, 2)
        self.assertIn("protected branch 'codex/next'", result.stderr)
        self.assertIn("git switch -c codex/next-task", result.stderr)

    def test_blocks_codex_master(self) -> None:
        result = self.run_guard("--branch", "codex/master", "--task", "hotfix")

        self.assertEqual(result.returncode, 2)
        self.assertIn("protected branch 'codex/master'", result.stderr)
        self.assertIn("git switch -c codex/master-hotfix", result.stderr)

    def test_allows_version_master_branch(self) -> None:
        result = self.run_guard("--branch", "codex/v0.4-master")

        self.assertEqual(result.returncode, 0)
        self.assertIn("allowed for direct commits", result.stdout)

    def test_allows_override_on_protected_branch(self) -> None:
        result = self.run_guard(
            "--branch",
            "codex/next",
            "--allow-protected",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Protected branch 'codex/next' allowed", result.stdout)
