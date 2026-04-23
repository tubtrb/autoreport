---
name: release-verification
description: Run release-time verification for the autoreport repository, including focused tests, browser smoke checks, cross-browser web demo validation, screenshot capture, download evidence, and verification-backed inputs for release notes or user guides. Use when Codex needs to decide if a version is ready to ship or gather fresh proof while drafting public docs.
---

# Release Verification

## Overview

Use this skill when a task is about release confidence rather than feature
implementation. It is especially useful when Codex should verify the current
release candidate, reproduce the user-facing flow in a browser, capture proof
artifacts, and feed those results into release notes or a user guide.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../../../README.md` and `../../../pyproject.toml`.
- Read `../../../docs/release-readiness.md`.
- Read `../public-repo-safety/SKILL.md` before declaring anything ready for public release.
- Read `references/release-checklist.md`.
- Read `references/browser-evidence.md` when browser screenshots or download proof are needed.
- If the task continues into tag creation, merged-source-branch cleanup, or `codex/next` refresh after signoff, also read `../release-tagging/SKILL.md`.
- Read the focused surface skill when verification targets one subsystem:
  - `../web-demo/SKILL.md` for homepage and `/api/generate`
  - `../release-docs/SKILL.md` for repo-tracked release wording
  - `../write-doc-markdown/SKILL.md` when public posts should reflect fresh verification
- If the release claim includes the public manual AI prompt/check/generate flow, also read `../../../docs/architecture/verif_test/04_result_review_gate.md`.
- Read the matching tests before claiming a contract is verified.

## Workflow

1. Define the release claim before testing.
- Identify the surface being signed off on: CLI, schema, PPTX output, web demo, or public docs.
- Turn user-facing claims into checks. Examples: "homepage loads", "example YAML generates a PPTX", "download starts in both Edge and Chrome".

2. Run the smallest relevant automated checks first.
- Use the repository virtualenv: `.\venv\Scripts\python.exe`.
- Prefer the narrow unittest targets from `AGENTS.md` before broader combinations.
- If the task is specifically about web release readiness, run `.\venv\Scripts\python.exe -m unittest tests.test_web_app` before browser automation.
- If the task is specifically about the public manual AI flow, run the narrow web tests first and then use the canonical low-trigger release-gate runner:
  First, if the profile is cold or challenge/login is expected, tell the user to seed the canonical profile manually from regular Chrome:
  ```powershell
  $chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
  if (-not (Test-Path $chrome)) {
    $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
  }
  $profile = Join-Path (Get-Location) ".codex\playwright\profiles\extai-chatgpt-spot"
  & $chrome --remote-debugging-port=9222 --user-data-dir="$profile" "https://chatgpt.com/"
  ```
  Then have them complete login/challenge, open one real conversation, optionally send one short message, and keep Chrome open.
  `powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http -SessionCheckOnly`
  `powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http`
- Keep `run_manual_ai_regression.ps1` for diagnostics and spot checks, not the release signoff path.
- For the current public-web evidence flow, prefer `.\venv\Scripts\python.exe tests/e2e/run_public_web_playwright.py --version <version>` after the narrow web tests. Install `-e .[e2e]` first when the optional Playwright extra is not available yet.

For the public manual AI path, the ChatGPT browser session must be the
user-opened regular Chrome session using
`.codex\playwright\profiles\extai-chatgpt-spot` plus the attach port. Do not
treat Whale or another regular browser window as equivalent regression state.

3. Reproduce the user-facing flow in a real browser.
- Prefer `playwright` for browser automation and screenshots.
- On Windows in this repo, use `msedge` first when it is already available, then run a cross-check in `chrome` when Chrome is installed.
- For the current web demo, verify:
  - `/healthz` responds successfully
  - `/` loads with the expected starter-manual copy
  - the public starter stays text-first and does not show image-upload controls
  - image-backed drafts are rejected on the public web path
  - the default or edited YAML can be generated without breaking the starter flow
  - PPTX generation starts an `autoreport_demo.pptx` download
  - the success state matches the current UI contract

4. Capture artifacts while the verification is fresh.
- Save browser screenshots under `output/playwright/`.
- Save public manual AI regression artifacts under `output/verif_test/`.
- Save temporary logs under `tests/_tmp/`.
- Record which browser was used, which URL was exercised, and whether the download event fired.
- The dedicated public-web runner also writes downloads under `.playwright-cli/downloads/` and can promote the `msedge` success capture into `docs/posts/guide-image-v<version>/image.png` when the user wants a guide-ready local asset.
- Keep generated output under `output/` or `.playwright-cli/` unless the user explicitly asks to promote a curated asset into docs.

5. Hand verified facts to documentation work.
- If the user is also writing release notes or a guide, pass only facts backed by tests or fresh browser evidence.
- Prefer wording like "verified on the current branch" when the evidence comes from this workspace rather than a public deployment URL.
- When a guide needs a screenshot, prefer the most readable success-state capture over a generic blank form.

6. Run the public safety gate before public signoff.
- Do not treat verification as sufficient on its own.
- If artifacts or docs are about to leave the private workspace, run `public-repo-safety` and respect any blocker findings.

## Current Repo Defaults

- The current product is a deterministic contract-first PPTX generator with CLI, a user-facing FastAPI app, and a separate debug FastAPI app.
- The web demo contract is anchored by `autoreport/web/app.py` and `tests/test_web_app.py`.
- The current success path returns a file download named `autoreport_demo.pptx`.
- Generated artifacts in `output/` are not for commit by default.
- The canonical public manual AI release gate is documented in `docs/architecture/verif_test/04_result_review_gate.md`.

## Output Contract

- State what was verified and what was not.
- Name the tests and browsers used.
- Provide artifact paths for screenshots, logs, or downloaded files when they informed the conclusion.
- Call out blockers or residual risk instead of silently assuming release readiness.
