## Autoreport v0.4.1 Release Notes

Release date: `2026-04-05`

Autoreport `v0.4.1` continues the `v0.4` line instead of jumping to `v0.5`. This release packages the screenshot-first manual procedure flow as the current public surface, keeps the deterministic CLI and debug paths aligned around the same runtime engine, and adds repeatable browser-evidence plus guide-handoff assets around that workflow.

## Live service

As of `2026-04-05`, the public release pages and the hosted demo app are available at:

- Release-facing site home: `http://auto-report.org/`
- Release-facing user guide: `http://auto-report.org/guide/`
- Release-facing updates hub: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo app: `http://3.36.96.47/`
- Alternate EC2 hostname: `http://ec2-3-36-96-47.ap-northeast-2.compute.amazonaws.com/`
- Hosted demo health check: `http://3.36.96.47/healthz` returns `{"status":"ok"}`

## What's included in this release

- Built-in `autoreport_manual` template support across the CLI, public web starter, and shared template flow
- Public homepage flow centered on the screenshot-first manual starter with `Refresh Slide Assets`, paired upload panels, and slide preview rows
- Public web generation that accepts the built-in manual upload flow while still blocking broader image-backed drafts outside that public path
- Stable launch entrypoints through `python -m autoreport.web.serve public|debug` plus the Windows wrappers `run-public.cmd` and `run-debug.cmd`
- Repeatable Playwright evidence capture for the manual public flow, including optional guide-image promotion
- Reusable static insert screenshots for Gemini, ChatGPT, and Claude, copied through the guide handoff path instead of being recaptured each release
- Release-facing posts and `autorelease` handoff inputs kept in repo-tracked `docs/posts/` source files

## Basic usage

CLI:

```bash
autoreport inspect-template --built-in autoreport_manual --output output/template_contract.yaml
autoreport scaffold-payload output/template_contract.yaml --output output/authoring_payload.yaml
autoreport compile-payload output/authoring_payload.yaml --built-in autoreport_manual --output output/report_payload.yaml
autoreport generate output/authoring_payload.yaml --built-in autoreport_manual --output output/autoreport_demo.pptx
```

If you want the editorial template instead of the manual procedure deck, replace `autoreport_manual` with `autoreport_editorial`.

Web demo:

```bash
python -m autoreport.web.serve public --host 0.0.0.0 --port 8000
```

On Windows from the repo root, you can also use:

```powershell
.\run-public.cmd
```

On the public homepage, start from the built-in manual procedure starter, keep the AI prompt comments attached when drafting elsewhere, use `Refresh Slide Assets`, upload the required screenshots beside the matching slide previews, and then select `Generate PPTX`. If a deck needs arbitrary template inspection or broader image-backed authoring, move that run to the debug app or CLI instead of widening the default homepage contract.

## Supported input structure

Autoreport currently exposes these public shapes:

- `template_contract`
- `report_content`
- `authoring_payload`
- `report_payload`

In the current release, `report_content` remains the primary AI-facing draft surface, `authoring_payload` is the normalized public authoring surface, and `report_payload` stays the compiled runtime surface.

## Output format

- CLI generation writes an editable `.pptx` to the requested output path
- The public web demo returns `autoreport_demo.pptx` as the immediate download filename
- The debug app keeps compiled and normalized views available for inspection before generation

## Verification on the current branch

This release note is based on the current workspace state on `codex/v0.4-master`.

- `.\venv\Scripts\python.exe -m unittest tests.test_cli tests.test_validator tests.test_generator tests.test_web_app tests.test_web_debug_app tests.test_web_serve tests.test_autorelease_handoff tests.test_public_web_playwright` passed
- `.\\venv\\Scripts\\python.exe tests\\e2e\\run_public_web_playwright.py --version 0.4.1 --promote-guide-image` is the repeatable browser evidence command for the current manual public flow
- Microsoft Edge and Chrome both observed `healthz` success and an `autoreport_demo.pptx` download on `2026-04-05`
- The public homepage opens with the manual procedure starter, aligned upload panels, and PowerPoint slide previews
- The built-in manual flow accepts the required screenshot uploads and downloads `autoreport_demo.pptx`
- The current browser-facing download contract remains `autoreport_demo.pptx`

## Current limitations

- Public web upload of arbitrary external PowerPoint templates is still not part of the default homepage flow
- The public web app intentionally keeps broader image-backed authoring and inspection in the separate debug app and CLI
- Final WordPress publication still runs from the private `autorelease` repository after handoff validation
- This release keeps the product in the `v0.4` line; it does not claim a broader new `v0.5` contract surface yet

## Next steps

- Publish the refreshed guide and updates through `autorelease`
- Add a public downloadable sample deck once the release asset is hosted
- Keep hardening the `v0.4.x` manual flow before deciding whether a larger `v0.5` surface is warranted
