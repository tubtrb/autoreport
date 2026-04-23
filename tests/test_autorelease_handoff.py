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
sync_standalone_pages = HANDOFF_MODULE.sync_standalone_pages
transform_homepage_body = HANDOFF_MODULE.transform_homepage_body
transform_guide_body = HANDOFF_MODULE.transform_guide_body
transform_release_notes_body = HANDOFF_MODULE.transform_release_notes_body
load_public_service_info = HANDOFF_MODULE.load_public_service_info
HandoffError = HANDOFF_MODULE.HandoffError


class HandoffRewriteTestCase(unittest.TestCase):
    """Keep the guide and release-note handoff rewrites aligned with v0.3 copy."""

    def make_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            version="0.3.0",
            source_ref="codex/v0.3-master",
            public_service_info=PublicServiceInfo(
                as_of="2026-03-29",
                release_home="http://auto-report.org/",
                release_guide="http://auto-report.org/guide/",
                release_updates="http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/",
                hosted_demo_primary="http://3.36.96.47/",
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
            "This guide reflects the public Autoreport experience for v0.3.0. Extra context stays here.",
            rewritten,
        )
        self.assertIn(
            "In the hosted demo, the success state changes to `Generation complete.`",
            rewritten,
        )
        self.assertIn("![Demo](../assets/guide/image.png)", rewritten)
        self.assertIn("## Browser check", rewritten)
        self.assertIn(
            "The hosted demo flow and the download were checked in the browser.",
            rewritten,
        )
        self.assertIn("## Open the hosted demo now", rewritten)
        self.assertIn(
            "[Open the hosted Autoreport demo](http://3.36.96.47/)",
            rewritten,
        )
        self.assertIn(
            "[Open the Updates page](http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/)",
            rewritten,
        )
        self.assertNotIn("codex/v0.3-master", rewritten)
        self.assertNotIn("The current branch was verified", rewritten)
        self.assertNotIn("healthz", rewritten)
        self.assertNotIn("## Live service", rewritten)

    def test_transform_guide_body_rewrites_placeholder_image_and_drops_local_comment(self) -> None:
        body = "\n".join(
            [
                "# User Guide",
                "",
                "Version: `v0.3.1`",
                "",
                "Status: `draft`",
                "",
                "## Hosted demo flow",
                "",
                "Guide body.",
                "",
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
        self.assertLess(
            rewritten.index("## Open the hosted demo now"),
            rewritten.index("## Hosted demo flow"),
        )
        self.assertNotIn("REPLACE_WITH_PUBLIC_IMAGE_URL", rewritten)
        self.assertNotIn("Local working screenshot asset", rewritten)
        self.assertNotIn("## Live service", rewritten)

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
            "Guide: `http://auto-report.org/guide/`",
            rewritten,
        )
        self.assertIn("## Browser check", rewritten)
        self.assertIn(
            "This release note reflects the public Autoreport v0.3.0 release surface.",
            rewritten,
        )
        self.assertNotIn("codex/v0.3-master", rewritten)

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
                "",
                "At this stage the public product story is aligned to the current `v0.4.1` release content, so readers can move between overview, guide, and updates without stepping into an older narrative.",
            ]
        )

        rewritten = transform_homepage_body(body, self.make_args())

        self.assertIn("## Live service", rewritten)
        self.assertIn("Hosted demo: `http://3.36.96.47/`", rewritten)
        self.assertNotIn("Old live service text.", rewritten)
        self.assertNotIn("healthz", rewritten)
        self.assertIn(
            "At this stage the public product story is aligned to the current `v0.3.0` release content, so readers can move between overview, guide, and updates without stepping into an older narrative.",
            rewritten,
        )
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
                version="0.3.0",
                public_service_info=self.make_args().public_service_info,
            )

            written_path = sync_homepage_live_service(args)
            rewritten = written_path.read_text(encoding="utf-8")

        self.assertEqual(written_path, homepage_path)
        self.assertIn("title: Home", rewritten)
        self.assertIn("## Live service", rewritten)
        self.assertIn("Hosted demo: `http://3.36.96.47/`", rewritten)
        self.assertIn("## Product overview", rewritten)
        self.assertNotIn("healthz", rewritten)

    def test_sync_standalone_pages_copies_docs_pages_sources(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as autorelease_dir:
            repo_root = Path(repo_dir)
            source_path = repo_root / "docs" / "pages" / "about.md"
            source_path.parent.mkdir(parents=True)
            source_text = "\n".join(
                [
                    "---",
                    "content_type: page",
                    "title: About",
                    "slug: about",
                    'summary: "About page"',
                    "date: 2026-04-11",
                    "status: publish",
                    "---",
                    "",
                    "# About",
                    "",
                    "Body text.",
                    "",
                ]
            )
            source_path.write_text(source_text, encoding="utf-8")

            args = argparse.Namespace(
                repo_root=repo_root,
                autorelease_root=Path(autorelease_dir),
            )

            written_paths = sync_standalone_pages(args)
            copied_path = Path(autorelease_dir) / "content" / "pages" / "about.md"

            self.assertEqual([copied_path], written_paths)
            self.assertTrue(copied_path.exists())
            self.assertEqual(source_text, copied_path.read_text(encoding="utf-8"))

    def test_sync_standalone_pages_rejects_reserved_main_source(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as autorelease_dir:
            repo_root = Path(repo_dir)
            source_path = repo_root / "docs" / "pages" / "main.md"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("# reserved\n", encoding="utf-8")

            args = argparse.Namespace(
                repo_root=repo_root,
                autorelease_root=Path(autorelease_dir),
            )

            with self.assertRaises(HandoffError):
                sync_standalone_pages(args)

    def test_load_public_service_info_does_not_require_alternate_hostname(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            info_path = repo_root / "docs" / "deployment" / "public-service-info.yaml"
            info_path.parent.mkdir(parents=True)
            info_path.write_text(
                "\n".join(
                    [
                        "as_of: 2026-04-11",
                        "release_site:",
                        '  home: "http://auto-report.org/"',
                        '  guide: "http://auto-report.org/guide/"',
                        '  updates: "http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/"',
                        "hosted_demo:",
                        '  primary: "http://3.36.96.47/"',
                        '  healthcheck: "http://3.36.96.47/healthz"',
                        '  healthcheck_expected: "{\\"status\\":\\"ok\\"}"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            info = load_public_service_info(repo_root)

        self.assertEqual("2026-04-11", info.as_of)
        self.assertEqual("http://3.36.96.47/", info.hosted_demo_primary)
        self.assertEqual("http://3.36.96.47/healthz", info.hosted_demo_healthcheck)


if __name__ == "__main__":
    unittest.main()
