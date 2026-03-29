# Release Readiness

This note captures the currently verified public release surface for
`autoreport`. It is intentionally limited to behavior that already exists in
the codebase and is backed by the current narrow checks.

## Verified User Flows

- CLI contract inspection with `inspect-template`
- CLI payload scaffolding with `scaffold-payload`
- CLI PPTX generation with `generate`
- Web demo homepage rendering, healthcheck, and PPTX download
- Web demo image upload refs such as `image_1`

## Narrow Verification Commands

Run these first when tightening release-facing wording:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_cli
.\venv\Scripts\python.exe -m unittest tests.test_web_app
```

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
example both keep the `text_image` and `image_1` reference path visible as
shared contract examples. The smoke command above uses a minimal runnable
payload fixture so release-prep docs do not need to rewrite that shared example
file.

## Current Release Scope

- The CLI can inspect the built-in editorial template or a user-supplied `.pptx` template.
- The public web demo exposes only the built-in editorial contract and payload flow.
- The web demo accepts uploaded `.png`, `.jpg`, and `.jpeg` files and binds them through `image_*` refs.
- The download path cleans up temporary output after the response is sent.

## Remaining Gaps Before Final Release Wrap-Up

- Public web upload of arbitrary external PowerPoint templates is not part of the current demo surface.
- This branch does not perform the final version bump, tag creation, or release publication.
- Additional release notes or publishing handoff should wait until the active runtime branches land.

## Source Of Truth

- `README.md`
- `pyproject.toml`
- `autoreport/cli.py`
- `autoreport/template_flow.py`
- `autoreport/web/app.py`
- `tests/test_cli.py`
- `tests/test_web_app.py`
