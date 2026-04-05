# Release Readiness

This note captures the currently verified public release surface for
`autoreport`. It is intentionally limited to behavior that already exists in
the codebase and is backed by the current narrow checks.

## Verified User Flows

- CLI contract inspection for built-in editorial/manual templates and user-supplied `.pptx` templates
- CLI payload scaffolding with `scaffold-payload`
- CLI authoring/report-content compilation with `compile-payload`
- CLI PPTX generation with `generate`
- Web demo homepage rendering, screenshot-first manual starter, slide-asset refresh, paired upload panels, healthcheck, and PPTX download
- Public web rejection of broader image-backed drafts outside the built-in manual upload path

## Narrow Verification Commands

Run these first when tightening release-facing wording:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_cli
.\venv\Scripts\python.exe -m unittest tests.test_web_app
.\venv\Scripts\python.exe -m unittest tests.test_web_serve
.\venv\Scripts\python.exe -m unittest tests.test_public_web_playwright
```

For repeatable public-web browser evidence and guide-image promotion, install the
optional e2e dependency and run the dedicated Playwright runner:

```powershell
.\venv\Scripts\python.exe -m pip install -e .[e2e]
.\venv\Scripts\python.exe tests/e2e/run_public_web_playwright.py --version 0.4.1
.\venv\Scripts\python.exe tests/e2e/run_public_web_playwright.py --version 0.4.1 --promote-guide-image
```

The runner writes raw screenshots under `output/playwright/v0.4.1/`,
downloads under `.playwright-cli/downloads/v0.4.1/`, a summary JSON under
`tests/_tmp/`, and the promoted guide image to
`docs/posts/guide-image-v0.4.1/image.png` when requested.

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

- The CLI can inspect the built-in editorial or manual template, or a user-supplied `.pptx` template.
- The CLI can compile and generate both editorial and manual built-in examples through the same deterministic runtime path.
- The public web demo exposes the built-in manual procedure starter with paired screenshot upload and preview rows.
- The public web demo supports the built-in manual upload flow and still rejects broader image-backed drafts outside that public path.
- Image-backed drafts remain available through the CLI and the separate debug web app.
- Public release evidence for the current manual flow is expected to come from the dedicated Playwright runner.
- The download path cleans up temporary output after the response is sent.

## Remaining Gaps Before Final Release Wrap-Up

- Public web upload of arbitrary external PowerPoint templates is not part of the current demo surface.
- Final WordPress publish still happens from the private `autorelease` repository after handoff validation.
- Some deeper internal architecture notes still keep legacy weekly-era wording outside the release-facing docs touched here.

## Source Of Truth

- `README.md`
- `pyproject.toml`
- `autoreport/cli.py`
- `autoreport/template_flow.py`
- `autoreport/web/app.py`
- `tests/test_cli.py`
- `tests/test_web_app.py`
