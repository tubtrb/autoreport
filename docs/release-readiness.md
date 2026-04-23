# Release Readiness

This note captures the currently verified public release surface for
`autoreport`. It is intentionally limited to behavior that already exists in
the codebase and is backed by the current narrow checks.

## Verified User Flows

- CLI contract inspection for built-in editorial/manual templates and
  user-supplied `.pptx` templates
- CLI payload scaffolding with `scaffold-payload`
- CLI authoring/report-content compilation with `compile-payload`
- CLI PPTX generation with `generate`
- Web demo homepage rendering, screenshot-first manual starter, `Check Draft`,
  `Refresh Preview`, supported add/remove controls, paired upload panels,
  healthcheck, and PPTX download
- Public web rejection of broader image-backed drafts outside the built-in
  manual upload path
- Public manual AI regression batching from
  `ChatGPT -> /api/manual-draft-check -> /api/generate -> PPTX inspection`,
  with fixed representative visual review cases

## Narrow Verification Commands

Run these first when tightening release-facing wording:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_cli
.\venv\Scripts\python.exe -m unittest tests.test_web_app
.\venv\Scripts\python.exe -m unittest tests.test_web_serve
.\venv\Scripts\python.exe -m unittest tests.test_public_web_playwright
```

The canonical public-manual AI regression runbook now lives under:

- `docs/architecture/verif_test/01_slide_patterns.md`
- `docs/architecture/verif_test/02_prompt_yaml_generation.md`
- `docs/architecture/verif_test/03_ai_batch_run_logging.md`
- `docs/architecture/verif_test/04_result_review_gate.md`

Use the canonical operator entrypoints instead of maintaining a second
release-only runbook here:

```powershell
powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http
```

Use `run_manual_ai_regression.ps1` for diagnostics and spot checks. Use
`run_manual_ai_release_gate.ps1` for the official low-trigger ChatGPT web
release gate.

The runner must not open the ChatGPT browser itself. `-Session` is the
canonical profile key for the manually opened Chrome session that the runner
attaches to.

- Canonical profile: `.codex\playwright\profiles\extai-chatgpt-spot`
- Remembered last-success URL:
  `.codex\playwright\extai-chatgpt-spot-last-url.txt`
- Legacy one-time recovery source: `output\playwright\chrome-userdata-copy`

`-SessionCheckOnly` attaches to the already-open Chrome session and validates
readiness across all `chatgpt.com` pages plus recent network responses. It is
the release-facing gate for challenge/login drift before the low-trigger 20-chat
runbook starts.

When the profile is cold or recently challenge-blocked, open it first from a
regular terminal-launched Chrome session:

```powershell
$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
  $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}
$profile = Join-Path (Get-Location) ".codex\playwright\profiles\extai-chatgpt-spot"
& $chrome --remote-debugging-port=9222 --user-data-dir="$profile" "https://chatgpt.com/"
```

In that regular Chrome session, complete login or Cloudflare approval, open one
real ChatGPT conversation, optionally send one short message, then keep Chrome
open before running `-SessionCheckOnly`.

The official release-gate schedule is one paced single-session 20-chat run:

1. manual profile open in terminal-launched regular Chrome with the attach port
2. `run_manual_ai_release_gate.ps1 -SessionCheckOnly`
3. Chunk A `smoke` 3 chats
4. cooldown 5 minutes
5. Chunk B `regression` 5 chats
6. cooldown 10 minutes
7. Chunk C `full` 6 chats
8. cooldown 15 minutes
9. Chunk D fixed repeat set 6 chats

Inside chunks, the runner idles 45 seconds after each completed case and adds 3
more minutes after every 3 completed chats. If ChatGPT shows challenge, login,
or auth watchdog failures mid-run, the gate stops and fails clearly without
browser relaunch escalation.

For repeatable public-web browser evidence and guide-image promotion, install the
optional e2e dependency and run the dedicated Playwright runner:

```powershell
.\venv\Scripts\python.exe -m pip install -e .[e2e]
.\venv\Scripts\python.exe tests/e2e/run_public_web_playwright.py --version 0.4.2
.\venv\Scripts\python.exe tests/e2e/run_public_web_playwright.py --version 0.4.2 --promote-guide-image
```

The runner writes raw screenshots under `output/playwright/v0.4.2/`,
downloads under `.playwright-cli/downloads/v0.4.2/`, a summary JSON under
`tests/_tmp/`, and the promoted guide image to
`docs/posts/guide-image-v0.4.2/image.png` when requested.

The release-prep CLI flow can also be smoke-tested directly with a minimal
runnable payload fixture:

```powershell
$smokeDir = "tests/_tmp/release-readiness"
New-Item -ItemType Directory -Force -Path $smokeDir | Out-Null
.\venv\Scripts\python.exe -m autoreport.cli inspect-template --built-in autoreport_editorial --output tests/_tmp/release-readiness/template_contract.yaml
.\venv\Scripts\python.exe -m autoreport.cli scaffold-payload tests/_tmp/release-readiness/template_contract.yaml --output tests/_tmp/release-readiness/report_payload.yaml
@'
report_payload:
  payload_version: autoreport.payload.v1
  template_id: autoreport-editorial-v1
  title_slide:
    title: Autoreport
    subtitle:
      - Template-aware PPTX autofill engine
  contents:
    enabled: true
  slides:
    - kind: text
      pattern_id: text.editorial
      title: What It Does
      include_in_contents: true
      body:
        - Generate editable PowerPoint decks from structured inputs.
      slot_overrides: {}
    - kind: metrics
      pattern_id: metrics.editorial
      title: Adoption Snapshot
      include_in_contents: true
      items:
        - label: Templates profiled
          value: 12
      slot_overrides: {}
'@ | Set-Content "$smokeDir/report_payload_smoke.yaml"
.\venv\Scripts\python.exe -m autoreport.cli generate tests/_tmp/release-readiness/report_payload_smoke.yaml --output tests/_tmp/release-readiness/autoreport_demo.pptx
```

Note: the scaffolded built-in editorial payload and the checked-in editorial
example still keep the `text_image` and `image_1` reference path visible as
shared cross-surface contract examples. The smoke command above uses a minimal
runnable text-and-metrics fixture so public release-prep docs do not depend on
the image-backed path.

## Current Release Scope

- The CLI can inspect the built-in editorial or manual template, or a
  user-supplied `.pptx` template.
- The CLI can compile and generate both editorial and manual built-in examples
  through the same deterministic runtime path.
- The public web demo exposes the built-in manual procedure starter,
  `Check Draft`, `Refresh Preview`, supported manual slide add/delete controls,
  and paired screenshot upload plus preview rows.
- The public web demo supports the built-in manual upload flow and still rejects
  broader image-backed drafts outside that public path.
- Image-backed drafts remain available through the CLI and the separate debug
  web app.
- Homepage/download browser evidence still comes from the dedicated Playwright
  runner.
- Public manual AI diagnostics follow `docs/architecture/verif_test/*` plus
  `run_manual_ai_regression.ps1`.
- Public manual AI release signoff follows the same docs plus
  `run_manual_ai_release_gate.ps1`.
- The download path cleans up temporary output after the response is sent.

## Remaining Gaps Before Final Release Wrap-Up

- Public web upload of arbitrary external PowerPoint templates is not part of
  the current demo surface.
- Mobile or phone support is not separately signed off for `v0.4.2`.
- The public site narrative may still be on `v0.4.1` until the `v0.4.2`
  candidate handoff is published.
- Final WordPress publish still happens from the private `autorelease`
  repository after handoff validation.
- Some deeper internal architecture notes still keep legacy weekly-era wording
  outside the release-facing docs touched here.

## Source Of Truth

- `README.md`
- `pyproject.toml`
- `autoreport/cli.py`
- `autoreport/template_flow.py`
- `autoreport/web/app.py`
- `tests/test_cli.py`
- `tests/test_web_app.py`
- `tests/test_web_serve.py`
- `tests/test_verif_test.py`
- `docs/architecture/verif_test/04_result_review_gate.md`
