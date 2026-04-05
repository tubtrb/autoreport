"""Unit tests for the public web Playwright evidence runner helpers."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "e2e"
    / "run_public_web_playwright.py"
)

SPEC = importlib.util.spec_from_file_location("run_public_web_playwright", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER_MODULE
SPEC.loader.exec_module(RUNNER_MODULE)

build_artifact_paths = RUNNER_MODULE.build_artifact_paths
build_screenshot_paths = RUNNER_MODULE.build_screenshot_paths
normalize_version_label = RUNNER_MODULE.normalize_version_label
promote_guide_assets = RUNNER_MODULE.promote_guide_assets
promote_guide_image = RUNNER_MODULE.promote_guide_image
read_project_version = RUNNER_MODULE.read_project_version


class PublicWebPlaywrightHelperTestCase(unittest.TestCase):
    def test_normalize_version_label_prefixes_plain_version(self) -> None:
        self.assertEqual(normalize_version_label("0.3.1"), "v0.3.1")
        self.assertEqual(normalize_version_label("v0.3.1"), "v0.3.1")

    def test_build_artifact_paths_follow_repo_convention(self) -> None:
        root = Path("C:/repo").resolve()
        paths = build_artifact_paths(root, "0.3.1", "msedge")

        self.assertEqual(
            paths["screenshot_dir"],
            root / "output" / "playwright" / "v0.3.1" / "msedge",
        )
        self.assertEqual(
            paths["download_dir"],
            root / ".playwright-cli" / "downloads" / "v0.3.1" / "msedge",
        )
        self.assertEqual(
            paths["guide_image"],
            root / "docs" / "posts" / "guide-image-v0.3.1" / "image.png",
        )

    def test_promote_guide_image_copies_success_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            success_capture = root / "output" / "playwright" / "v0.3.1" / "msedge" / "generation-success-full.png"
            success_capture.parent.mkdir(parents=True)
            success_capture.write_bytes(b"png-bytes")

            promoted = promote_guide_image(root, "0.3.1", success_capture)

            self.assertEqual(
                promoted,
                root / "docs" / "posts" / "guide-image-v0.3.1" / "image.png",
            )
            self.assertEqual(promoted.read_bytes(), b"png-bytes")

    def test_build_screenshot_paths_use_action_focused_names(self) -> None:
        screenshot_dir = Path("C:/repo/output/playwright/v0.3.1/msedge")
        paths = build_screenshot_paths(screenshot_dir)

        self.assertEqual(
            paths["starter_loaded"],
            screenshot_dir / "01-manual-starter-loaded.png",
        )
        self.assertEqual(
            paths["upload_row_filled"],
            screenshot_dir / "03-upload-row-filled.png",
        )
        self.assertEqual(
            paths["generation_success"],
            screenshot_dir / "05-generate-success.png",
        )

    def test_promote_guide_assets_copies_named_screenshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            guide_dir = root / "docs" / "posts" / "guide-image-v0.3.1"
            screenshot_dir = root / "output" / "playwright" / "v0.3.1" / "msedge"
            screenshot_dir.mkdir(parents=True)
            screenshot_paths = {
                "starter_loaded": str(screenshot_dir / "01-manual-starter-loaded.png"),
                "generation_success": str(screenshot_dir / "05-generate-success.png"),
            }
            for source in screenshot_paths.values():
                Path(source).write_bytes(b"png")

            promoted_dir = promote_guide_assets(root, "0.3.1", screenshot_paths)

            self.assertEqual(promoted_dir, guide_dir)
            self.assertEqual(
                (guide_dir / "01-manual-starter-loaded.png").read_bytes(),
                b"png",
            )
            self.assertEqual(
                (guide_dir / "05-generate-success.png").read_bytes(),
                b"png",
            )

    def test_read_project_version_uses_pyproject_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[project]",
                        'version = "0.4.0"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(read_project_version(root), "0.4.0")


if __name__ == "__main__":
    unittest.main()
