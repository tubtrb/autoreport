"""Capture Playwright evidence for the public Autoreport web app."""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII="
)
REQUIRED_UI_TEXT = (
    "Manual Procedure Starter",
    "Reset Starter Example",
    "Refresh Slide Assets",
    "Generate PPTX",
    "PowerPoint Slide Preview",
)
EXPECTED_DOWNLOAD_NAME = "autoreport_demo.pptx"
SCREENSHOT_FILE_NAMES = {
    "starter_loaded": "01-manual-starter-loaded.png",
    "refresh_complete": "02-refresh-slide-assets-complete.png",
    "upload_row_filled": "03-upload-row-filled.png",
    "generate_in_progress": "04-generate-in-progress.png",
    "generation_success": "05-generate-success.png",
}
ACTION_OVERLAY_ID = "__autoreport_action_overlay"
WINDOWS_BROWSER_PATHS = {
    "msedge": (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ),
    "chrome": (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ),
}


@dataclass(frozen=True)
class BrowserTarget:
    """One browser channel to exercise through Playwright."""

    name: str
    channel: str
    executable_path: Path


@dataclass
class BrowserRunSummary:
    """Minimal machine-readable facts from one browser evidence run."""

    version: str
    browser: str
    route: str
    download_filename: str
    download_observed: bool
    healthcheck_ok: bool
    started_at: str
    finished_at: str
    screenshots: dict[str, str]
    download_path: str
    video_path: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_project_version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as handle:
        payload = tomllib.load(handle)
    version = payload.get("project", {}).get("version")
    if not version:
        raise RuntimeError("Could not find project.version in pyproject.toml.")
    return str(version)


def normalize_version_label(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def default_route_host(host: str) -> str:
    return "127.0.0.1" if host == "0.0.0.0" else host


def find_browser_targets() -> list[BrowserTarget]:
    targets: list[BrowserTarget] = []
    for name in ("msedge", "chrome"):
        executable = next(
            (candidate for candidate in WINDOWS_BROWSER_PATHS[name] if candidate.exists()),
            None,
        )
        if executable is None:
            if name == "msedge":
                raise RuntimeError(
                    "Microsoft Edge is required for the public web evidence run."
                )
            continue
        targets.append(
            BrowserTarget(
                name=name,
                channel=name,
                executable_path=executable,
            )
        )
    return targets


def build_artifact_paths(root: Path, version: str, browser: str) -> dict[str, Path]:
    version_label = normalize_version_label(version)
    return {
        "screenshot_dir": root / "output" / "playwright" / version_label / browser,
        "download_dir": root
        / ".playwright-cli"
        / "downloads"
        / version_label
        / browser,
        "video_dir": root / ".playwright-cli" / "videos" / version_label / browser,
        "guide_image": root / "docs" / "posts" / f"guide-image-{version_label}" / "image.png",
    }


def create_input_pngs(root: Path, version: str) -> list[Path]:
    input_dir = root / "tests" / "_tmp" / "playwright-inputs" / normalize_version_label(version)
    if input_dir.exists():
        shutil.rmtree(input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index in range(1, 7):
        path = input_dir / f"image_{index}.png"
        path.write_bytes(PNG_BYTES)
        paths.append(path)
    return paths


def build_screenshot_paths(screenshot_dir: Path) -> dict[str, Path]:
    return {
        key: screenshot_dir / filename
        for key, filename in SCREENSHOT_FILE_NAMES.items()
    }


def wait_for_healthcheck(route: str, *, timeout_seconds: float = 30.0) -> bool:
    health_url = f"{route.rstrip('/')}/healthz"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(health_url, timeout=2.0)
            if response.status_code == 200 and response.json() == {"status": "ok"}:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def load_playwright():
    try:
        from playwright.sync_api import Error, TimeoutError, sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on local optional install
        raise RuntimeError(
            "Playwright is not installed. Run `.\\venv\\Scripts\\python.exe -m pip install -e .[e2e]` first."
        ) from exc
    return sync_playwright, TimeoutError, Error


def launch_public_server(root: Path, *, host: str, port: int, log_path: Path) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "autoreport.web.serve",
            "public",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=root,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def promote_guide_image(root: Path, version: str, source_image: Path) -> Path:
    target = build_artifact_paths(root, version, "msedge")["guide_image"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_image, target)
    return target


def promote_guide_assets(root: Path, version: str, screenshot_paths: dict[str, str]) -> Path:
    guide_image = build_artifact_paths(root, version, "msedge")["guide_image"]
    guide_dir = guide_image.parent
    guide_dir.mkdir(parents=True, exist_ok=True)
    for source in screenshot_paths.values():
        source_path = Path(source)
        if source_path.exists():
            shutil.copy2(source_path, guide_dir / source_path.name)
    return guide_dir


def capture_top_viewport(page, path: Path) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(path), full_page=False)


def clear_action_overlay(page) -> None:
    page.evaluate(
        """(overlayId) => {
            const existing = document.getElementById(overlayId);
            if (existing) {
              existing.remove();
            }
        }""",
        ACTION_OVERLAY_ID,
    )


def show_action_overlay(page, locator, *, label: str) -> None:
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if box is None:
        raise AssertionError("Could not determine action target bounds for overlay capture.")
    page.evaluate(
        """({ overlayId, left, top, width, height, label }) => {
            const previous = document.getElementById(overlayId);
            if (previous) {
              previous.remove();
            }
            const overlay = document.createElement("div");
            overlay.id = overlayId;
            overlay.style.position = "fixed";
            overlay.style.left = `${left}px`;
            overlay.style.top = `${top}px`;
            overlay.style.width = `${width}px`;
            overlay.style.height = `${height}px`;
            overlay.style.pointerEvents = "none";
            overlay.style.zIndex = "2147483647";
            overlay.style.boxSizing = "border-box";

            const outline = document.createElement("div");
            outline.style.position = "absolute";
            outline.style.inset = "-6px";
            outline.style.border = "4px solid #ef4444";
            outline.style.borderRadius = "16px";
            outline.style.boxShadow = "0 0 0 10px rgba(239, 68, 68, 0.18)";
            overlay.appendChild(outline);

            const tag = document.createElement("div");
            tag.textContent = label;
            tag.style.position = "absolute";
            tag.style.top = "-50px";
            tag.style.left = "0";
            tag.style.padding = "10px 16px";
            tag.style.borderRadius = "999px";
            tag.style.background = "#111827";
            tag.style.color = "#ffffff";
            tag.style.font = "800 16px/1.2 'Segoe UI', Arial, sans-serif";
            tag.style.letterSpacing = "0.01em";
            tag.style.boxShadow = "0 12px 30px rgba(15, 23, 42, 0.28)";
            tag.style.whiteSpace = "nowrap";
            overlay.appendChild(tag);

            document.body.appendChild(overlay);
        }""",
        {
            "overlayId": ACTION_OVERLAY_ID,
            "left": box["x"],
            "top": box["y"],
            "width": box["width"],
            "height": box["height"],
            "label": label,
        },
    )


def capture_top_viewport_with_overlay(page, path: Path, *, locator, label: str) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    show_action_overlay(page, locator, label=label)
    page.screenshot(path=str(path), full_page=False)
    clear_action_overlay(page)


def capture_locator_clip_with_overlay(
    page,
    *,
    clip_locator,
    target_locator,
    label: str,
    path: Path,
    padding: int = 16,
) -> None:
    clip_locator.scroll_into_view_if_needed()
    show_action_overlay(page, target_locator, label=label)
    box = clip_locator.bounding_box()
    if box is None:
        clear_action_overlay(page)
        raise AssertionError("Could not determine clip bounds for overlay capture.")
    viewport = page.viewport_size or {"width": 1600, "height": 1200}
    clip_x = max(box["x"] - padding, 0)
    clip_y = max(box["y"] - padding, 0)
    clip_width = min(viewport["width"] - clip_x, box["width"] + (padding * 2))
    clip_height = min(viewport["height"] - clip_y, box["height"] + (padding * 2))
    page.screenshot(
        path=str(path),
        clip={
            "x": clip_x,
            "y": clip_y,
            "width": clip_width,
            "height": clip_height,
        },
    )
    clear_action_overlay(page)


def run_browser_evidence(
    *,
    target: BrowserTarget,
    route: str,
    input_paths: list[Path],
    root: Path,
    version: str,
    capture_video: bool,
    healthcheck_ok: bool,
) -> BrowserRunSummary:
    sync_playwright, playwright_timeout, playwright_error = load_playwright()
    artifacts = build_artifact_paths(root, version, target.name)
    screenshot_dir = artifacts["screenshot_dir"]
    download_dir = artifacts["download_dir"]
    video_dir = artifacts["video_dir"]
    for directory in (screenshot_dir, download_dir, video_dir):
        if directory.exists():
            shutil.rmtree(directory)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    if capture_video:
        video_dir.mkdir(parents=True, exist_ok=True)

    screenshot_paths = build_screenshot_paths(screenshot_dir)
    download_path = download_dir / EXPECTED_DOWNLOAD_NAME
    video_path: Path | None = (
        video_dir / f"{target.name}-session.webm" if capture_video else None
    )

    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with sync_playwright() as playwright:
        browser = None
        context = None
        page = None
        video = None
        try:
            browser = playwright.chromium.launch(headless=True, channel=target.channel)
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1600, "height": 1200},
                record_video_dir=str(video_dir) if capture_video else None,
            )
            page = context.new_page()
            video = page.video if capture_video else None

            page.goto(route, wait_until="networkidle", timeout=60_000)
            for text in REQUIRED_UI_TEXT:
                page.wait_for_function(
                    "(expectedText) => document.body.innerText.includes(expectedText)",
                    arg=text,
                    timeout=30_000,
                )
            page.wait_for_function(
                "() => document.querySelectorAll('.slide-upload-slot input[type=file]').length === 6",
                timeout=30_000,
            )
            capture_top_viewport_with_overlay(
                page,
                screenshot_paths["starter_loaded"],
                locator=page.locator("#payload-yaml"),
                label="Edit or paste YAML here",
            )

            file_inputs = page.locator(".slide-upload-slot input[type=file]")
            if file_inputs.count() != len(input_paths):
                raise AssertionError(
                    f"Expected {len(input_paths)} upload inputs, found {file_inputs.count()}."
                )
            for index, input_path in enumerate(input_paths):
                file_inputs.nth(index).set_input_files(str(input_path))

            page.get_by_role("button", name="Refresh Slide Assets").click()
            page.wait_for_function(
                "() => document.getElementById('status-message').textContent.includes('Manual slide assets refreshed.')",
                timeout=30_000,
            )
            capture_top_viewport_with_overlay(
                page,
                screenshot_paths["refresh_complete"],
                locator=page.get_by_role("button", name="Refresh Slide Assets"),
                label="Click Refresh Slide Assets",
            )
            first_upload_row = page.locator(".slide-preview-row.has-upload").first
            first_upload_slot = page.locator(".slide-upload-slot").first
            capture_locator_clip_with_overlay(
                page,
                clip_locator=first_upload_row,
                target_locator=first_upload_slot,
                label="Upload screenshot here",
                path=screenshot_paths["upload_row_filled"],
            )

            def delay_generate(route) -> None:
                time.sleep(0.8)
                route.continue_()

            page.route("**/api/generate", delay_generate)
            with page.expect_download(timeout=60_000) as download_info:
                page.get_by_role("button", name="Generate PPTX").click()
                page.wait_for_function(
                    "() => document.getElementById('status-message').textContent.includes('Validating the payload and generating your Autoreport deck...')",
                    timeout=5_000,
                )
                capture_top_viewport_with_overlay(
                    page,
                    screenshot_paths["generate_in_progress"],
                    locator=page.get_by_role("button", name="Generate PPTX"),
                    label="Click Generate PPTX",
                )
            page.unroute("**/api/generate", delay_generate)
            download = download_info.value
            page.wait_for_function(
                "() => document.getElementById('status-message').textContent.includes('Generation complete. Your Autoreport deck download should begin shortly.')",
                timeout=60_000,
            )
            capture_top_viewport_with_overlay(
                page,
                screenshot_paths["generation_success"],
                locator=page.get_by_role("button", name="Generate PPTX"),
                label="Generate PPTX clicked here",
            )

            suggested_filename = download.suggested_filename
            if suggested_filename != EXPECTED_DOWNLOAD_NAME:
                raise AssertionError(
                    f"Expected download filename {EXPECTED_DOWNLOAD_NAME!r}, got {suggested_filename!r}."
                )
            download.save_as(str(download_path))
        except (playwright_timeout, playwright_error) as exc:
            raise RuntimeError(
                f"Playwright run failed for {target.name} ({target.executable_path}): {exc}"
            ) from exc
        finally:
            if page is not None:
                page.close()
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()
            if capture_video and video is not None and video_path is not None:
                video.save_as(str(video_path))

    finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
    return BrowserRunSummary(
        version=version,
        browser=target.name,
        route=route,
        download_filename=EXPECTED_DOWNLOAD_NAME,
        download_observed=download_path.exists(),
        healthcheck_ok=healthcheck_ok,
        started_at=started_at,
        finished_at=finished_at,
        screenshots={key: str(path) for key, path in screenshot_paths.items()},
        download_path=str(download_path),
        video_path=str(video_path) if video_path and video_path.exists() else None,
    )


def write_summary(root: Path, version: str, route: str, results: list[BrowserRunSummary]) -> Path:
    summary_path = (
        root / "tests" / "_tmp" / f"playwright-summary-{normalize_version_label(version)}.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "version": version,
        "route": route,
        "results": [asdict(result) for result in results],
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Playwright evidence against the public Autoreport web app.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version label for artifact folders. Defaults to project.version.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the local public web server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the local public web server to.",
    )
    parser.add_argument(
        "--capture-video",
        action="store_true",
        help="Record local Playwright session video under .playwright-cli/videos/.",
    )
    parser.add_argument(
        "--promote-guide-image",
        action="store_true",
        help="Copy the msedge success screenshot to docs/posts/guide-image-v<version>/image.png.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    version = args.version or read_project_version(root)
    route = f"http://{default_route_host(args.host)}:{args.port}/"
    log_path = root / "tests" / "_tmp" / f"playwright-server-{normalize_version_label(version)}.log"
    targets = find_browser_targets()
    input_paths = create_input_pngs(root, version)
    server = launch_public_server(root, host=args.host, port=args.port, log_path=log_path)
    results: list[BrowserRunSummary] = []

    try:
        if not wait_for_healthcheck(route):
            raise RuntimeError(
                f"Public web server did not become healthy at {route}healthz. See {log_path}."
            )
        for target in targets:
            result = run_browser_evidence(
                target=target,
                route=route,
                input_paths=input_paths,
                root=root,
                version=version,
                capture_video=args.capture_video,
                healthcheck_ok=True,
            )
            results.append(result)
        summary_path = write_summary(root, version, route, results)
        print(f"Wrote Playwright summary to {summary_path}")
        if args.promote_guide_image:
            msedge_result = next(
                (result for result in results if result.browser == "msedge"),
                None,
            )
            if msedge_result is None:
                raise RuntimeError("Cannot promote guide image without a successful msedge run.")
            promote_guide_assets(root, version, msedge_result.screenshots)
            promoted_path = promote_guide_image(
                root,
                version,
                Path(msedge_result.screenshots["generation_success"]),
            )
            print(f"Promoted guide image to {promoted_path}")
        return 0
    finally:
        stop_server(server)


if __name__ == "__main__":
    raise SystemExit(main())
