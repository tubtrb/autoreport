"""Regression tests for the autorelease handoff rewrite helpers."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
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
PublicServiceInfo = HANDOFF_MODULE.PublicServiceInfo
build_specs = HANDOFF_MODULE.build_specs
sync_assets = HANDOFF_MODULE.sync_assets
sync_homepage_live_service = HANDOFF_MODULE.sync_homepage_live_service
transform_homepage_body = HANDOFF_MODULE.transform_homepage_body
transform_guide_body = HANDOFF_MODULE.transform_guide_body
transform_release_notes_body = HANDOFF_MODULE.transform_release_notes_body


class HandoffRewriteTestCase(unittest.TestCase):
    """Keep the guide and release-note handoff rewrites aligned with v0.3 copy."""

    def make_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            source_ref="codex/v0.3-master",
            public_service_info=PublicServiceInfo(
                as_of="2026-03-29",
                release_home="http://auto-report.org/",
                release_guide="http://auto-report.org/guide/",
                release_updates="http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/",
                hosted_demo_primary="http://3.36.96.47/",
                hosted_demo_alternate="http://ec2-3-36-96-47.ap-northeast-2.compute.amazonaws.com/",
                hosted_demo_healthcheck="http://3.36.96.47/healthz",
                hosted_demo_healthcheck_expected='{"status":"ok"}',
            ),
        )

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
        self.assertIn("## Live service", rewritten)
        self.assertIn("Release-facing site home: `http://auto-report.org/`", rewritten)
        self.assertIn("Hosted demo app: `http://3.36.96.47/`", rewritten)

    def test_transform_guide_body_rewrites_placeholder_image_and_drops_local_comment(self) -> None:
        body = "\n".join(
            [
                "# User Guide",
                "",
                "This guide reflects the current implementation of Autoreport on the active branch.",
                "",
                "![Autoreport web demo](REPLACE_WITH_PUBLIC_IMAGE_URL)",
                "",
                "<!-- Local working screenshot asset: docs/posts/guide-image-v0.3.1/image.png -->",
            ]
        )

        rewritten = transform_guide_body(body, self.make_spec(), self.make_args())

        self.assertIn(
            "![Autoreport web demo](../assets/guide/image.png)",
            rewritten,
        )
        self.assertNotIn("REPLACE_WITH_PUBLIC_IMAGE_URL", rewritten)
        self.assertNotIn("Local working screenshot asset", rewritten)

    def test_transform_guide_body_rewrites_shared_external_ai_insert_assets(self) -> None:
        body = "\n".join(
            [
                "# User Guide",
                "",
                "![Gemini starter brief](../shared-assets/user-guide-ai-insert/gemini-insert.png)",
                "![ChatGPT starter brief](../shared-assets/user-guide-ai-insert/chatgpt-insert.png)",
            ]
        )

        rewritten = transform_guide_body(body, self.make_spec(), self.make_args())

        self.assertIn(
            "![Gemini starter brief](../assets/guide/ai-insert/gemini-insert.png)",
            rewritten,
        )
        self.assertIn(
            "![ChatGPT starter brief](../assets/guide/ai-insert/chatgpt-insert.png)",
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
        self.assertIn("## Live service", rewritten)
        self.assertIn(
            "Release-facing user guide: `http://auto-report.org/guide/`",
            rewritten,
        )
        self.assertIn("## Verification for this release", rewritten)
        self.assertIn(
            "This release note reflects the `codex/v0.3-master` branch and its verification run.",
            rewritten,
        )

    def test_transform_homepage_body_normalizes_live_service_section(self) -> None:
        body = "\n".join(
            [
                "# Autoreport",
                "",
                "Intro paragraph.",
                "",
                "## Live service",
                "",
                "Old live service text.",
                "",
                "## Product overview",
                "",
                "- Overview bullet",
            ]
        )

        rewritten = transform_homepage_body(body, self.make_args())

        self.assertIn("## Live service", rewritten)
        self.assertIn("Hosted demo health check: `http://3.36.96.47/healthz`", rewritten)
        self.assertNotIn("Old live service text.", rewritten)
        self.assertLess(
            rewritten.index("## Live service"),
            rewritten.index("## Product overview"),
        )

    def test_build_specs_omits_cover_image_when_guide_asset_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as autorelease_dir:
            repo_root = Path(repo_dir)
            posts_root = repo_root / "docs" / "posts"
            posts_root.mkdir(parents=True)
            for name in (
                "autoreport-guide-v0.3.0.md",
                "autoreport-v0.3.0-release-notes.md",
                "autoreport-v0.3.0-development-log.md",
            ):
                (posts_root / name).write_text("# placeholder\n", encoding="utf-8")

            args = argparse.Namespace(
                repo_root=repo_root,
                autorelease_root=Path(autorelease_dir),
                version="0.3.0",
            )

            specs = build_specs(args)
            guide_spec = next(spec for spec in specs if spec.key == "guide")
            devlog_spec = next(spec for spec in specs if spec.key == "devlog")

            self.assertIsNone(guide_spec.source_asset_dir)
            self.assertIsNone(guide_spec.cover_image)
            self.assertIsNone(devlog_spec.source_asset_dir)

    def test_sync_assets_copies_shared_guide_insert_assets(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as autorelease_dir:
            repo_root = Path(repo_dir)
            source_path = repo_root / "docs" / "posts" / "autoreport-guide-v0.3.0.md"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("# placeholder\n", encoding="utf-8")
            shared_asset_dir = repo_root / "docs" / "shared-assets" / "user-guide-ai-insert"
            shared_asset_dir.mkdir(parents=True)
            (shared_asset_dir / "gemini-insert.png").write_bytes(b"png")

            spec = PostSpec(
                key="guide",
                section="guide",
                source_path=source_path,
                target_path=Path(autorelease_dir) / "content" / "guides" / "guide.md",
                slug="guide",
                title="User Guide",
                summary="Guide summary",
                tags=("user-guide",),
                transform_body=transform_guide_body,
                source_asset_dir=None,
                cover_image=None,
            )

            sync_assets(spec)

            copied_asset = (
                Path(autorelease_dir)
                / "content"
                / "assets"
                / "guide"
                / "ai-insert"
                / "gemini-insert.png"
            )
            self.assertTrue(copied_asset.exists())
            self.assertEqual(copied_asset.read_bytes(), b"png")

    def test_sync_homepage_live_service_updates_page_body(self) -> None:
        with tempfile.TemporaryDirectory() as autorelease_dir:
            homepage_path = Path(autorelease_dir) / "content" / "pages" / "main.md"
            homepage_path.parent.mkdir(parents=True)
            homepage_path.write_text(
                "\n".join(
                    [
                        "---",
                        "title: Home",
                        "slug: main",
                        "section: page",
                        "summary: Home page",
                        "date: 2026-03-29",
                        "status: draft",
                        "---",
                        "",
                        "# Autoreport",
                        "",
                        "Intro paragraph.",
                        "",
                        "## Product overview",
                        "",
                        "- Overview bullet",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            args = argparse.Namespace(
                autorelease_root=Path(autorelease_dir),
                public_service_info=self.make_args().public_service_info,
            )

            written_path = sync_homepage_live_service(args)
            rewritten = written_path.read_text(encoding="utf-8")

            self.assertEqual(written_path, homepage_path)
            self.assertIn("title: Home", rewritten)
            self.assertIn("## Live service", rewritten)
            self.assertIn("Hosted demo app: `http://3.36.96.47/`", rewritten)
            self.assertIn("## Product overview", rewritten)


if __name__ == "__main__":
    unittest.main()
