"""Regression tests for the autorelease handoff rewrite helpers."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "codex"
    / "skills"
    / "autorelease-handoff"
    / "scripts"
    / "handoff_posts_to_autorelease.py"
)

SPEC = importlib.util.spec_from_file_location("handoff_posts_to_autorelease", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
HANDOFF_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HANDOFF_MODULE
SPEC.loader.exec_module(HANDOFF_MODULE)

PostSpec = HANDOFF_MODULE.PostSpec
transform_guide_body = HANDOFF_MODULE.transform_guide_body
transform_release_notes_body = HANDOFF_MODULE.transform_release_notes_body


class HandoffRewriteTestCase(unittest.TestCase):
    """Keep the guide and release-note handoff rewrites aligned with v0.3 copy."""

    def make_args(self) -> argparse.Namespace:
        return argparse.Namespace(source_ref="codex/v0.3-master")

    def make_spec(self, *, slug: str = "guide", source_asset_dir: str = "guide-image-v0.3.0") -> object:
        return PostSpec(
            key="guide",
            section="guide",
            source_path=Path("docs/posts/autoreport-guide-v0.3.0.md"),
            target_path=Path("content/guides/guide.md"),
            slug=slug,
            title="User Guide",
            summary="Guide summary",
            tags=("user-guide",),
            transform_body=transform_guide_body,
            source_asset_dir=Path(source_asset_dir),
            cover_image=f"../assets/{slug}/image.png",
        )

    def test_transform_guide_body_rewrites_branch_relative_copy_and_assets(self) -> None:
        body = "\n".join(
            [
                "# User Guide",
                "",
                "This guide reflects the current implementation of Autoreport on the active branch. Extra context stays here.",
                "",
                "On the current branch, the success state changes to `Generation complete.`",
                "",
                "![Demo](guide-image-v0.3.0/image.png)",
                "",
                "## Verification on the current branch",
                "",
                "The current branch was verified with the contract-facing CLI and web test suites.",
            ]
        )

        rewritten = transform_guide_body(body, self.make_spec(), self.make_args())

        self.assertIn(
            "This guide reflects the Autoreport implementation at `codex/v0.3-master`. Extra context stays here.",
            rewritten,
        )
        self.assertIn(
            "In this handoff build, the success state changes to `Generation complete.`",
            rewritten,
        )
        self.assertIn("![Demo](../assets/guide/image.png)", rewritten)
        self.assertIn("## Verification for this handoff build", rewritten)
        self.assertIn(
            "The `codex/v0.3-master` build was verified with the contract-facing CLI and web test suites.",
            rewritten,
        )

    def test_transform_release_notes_body_rewrites_workspace_reference(self) -> None:
        body = "\n".join(
            [
                "The current branch now exposes the refreshed flow.",
                "",
                "## Verification on the current branch",
                "",
                "This release note is based on the current workspace state rather than a tagged public deployment.",
            ]
        )

        rewritten = transform_release_notes_body(body, self.make_spec(), self.make_args())

        self.assertIn("This release now exposes the refreshed flow.", rewritten)
        self.assertIn("## Verification for this release", rewritten)
        self.assertIn(
            "This release note reflects the `codex/v0.3-master` branch and its verification run.",
            rewritten,
        )


if __name__ == "__main__":
    unittest.main()
