## Autoreport v0.3.1 Release Notes

Release date: `2026-04-04`

Autoreport `v0.3.1` is a patch release that keeps the `v0.3` contract-first line intact while tightening the public release surface around it. The CLI and deterministic PPTX generation path stay the same, the public homepage now leads with the built-in screenshot-first manual procedure starter, broader image-backed drafts stay on the debug app or CLI path, and the release-facing guide plus handoff flow now point to the same live service information.

## Live service

As of `2026-04-04`, the public release pages and the hosted demo app are available at:

- Release-facing site home: `http://auto-report.org/`
- Release-facing user guide: `http://auto-report.org/guide/`
- Release-facing updates hub: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo app: `http://3.36.96.47/`
- Alternate EC2 hostname: `http://ec2-3-36-96-47.ap-northeast-2.compute.amazonaws.com/`
- Hosted demo health check: `http://3.36.96.47/healthz` returns `{"status":"ok"}`

## What's included in this release

- Public homepage guidance now stays centered on the built-in manual procedure starter with paired upload and preview rows
- The same contract-first CLI flow remains available for `inspect-template`, `scaffold-payload`, `compile-payload`, and `generate`
- The separate debug app remains available for contract inspection, compiled payload review, and image-backed draft work
- A repeatable Playwright evidence runner now captures homepage and success-state screenshots, downloads `autoreport_demo.pptx`, and can promote a guide cover image into `docs/posts/guide-image-v0.3.1/image.png`
- Release-facing service URLs and the private publishing handoff now stay aligned from tracked repo files
- The hosted download contract remains `autoreport_demo.pptx`

## Basic usage

CLI:

```bash
autoreport inspect-template --built-in autoreport_editorial --output output/template_contract.yaml
autoreport scaffold-payload output/template_contract.yaml --output output/authoring_payload.yaml
autoreport compile-payload output/authoring_payload.yaml --output output/report_payload.yaml
autoreport generate output/authoring_payload.yaml --output output/autoreport_demo.pptx
```

Web demo:

```bash
python -m autoreport.web.serve public --host 0.0.0.0 --port 8000
```

Debug app:

```bash
python -m autoreport.web.serve debug --host 0.0.0.0 --port 8010
```

On the public homepage, start from the built-in manual procedure starter, select `Refresh Slide Assets`, add the required screenshots in the aligned upload panels, and then select `Generate PPTX`. If a deck needs arbitrary template inspection or broader image-backed draft work, move that run to the debug app or the CLI instead of the default homepage path.

## Supported input structure

Autoreport currently exposes these public shapes:

- `template_contract`
- `report_content`
- `authoring_payload`
- `report_payload`

In the current release, `report_content` is the primary AI-facing draft surface, `authoring_payload` is the normalized public authoring surface, and `report_payload` remains the compiled runtime surface.

## Output format

- CLI generation writes an editable `.pptx` to the requested output path
- The public web demo returns `autoreport_demo.pptx` as the immediate download filename
- The debug app keeps the compiled and normalized views available for inspection before generation

## Verification on the current branch

This release note is based on the current workspace state on `codex/v0.3-master`.

- `.\venv\Scripts\python.exe -m unittest tests.test_web_app tests.test_web_debug_app tests.test_autorelease_handoff tests.test_public_web_playwright` passed
- `.\\venv\\Scripts\\python.exe tests\\e2e\\run_public_web_playwright.py --version 0.3.1` is the repeatable browser evidence command for the current hosted-flow contract
- The public homepage opens with the manual procedure starter, aligned upload panels, and PowerPoint slide previews
- The built-in manual flow accepts the required screenshot uploads and downloads `autoreport_demo.pptx`
- The debug app keeps `text_image` drafts available
- The current browser-facing download contract remains `autoreport_demo.pptx`

## Current limitations

- Public web upload of arbitrary external PowerPoint templates is still not part of the default homepage flow
- The public web app intentionally avoids debug panes and broad debug-only image authoring; those remain in the separate debug app and CLI
- Final WordPress publication still runs from the private `autorelease` repository after handoff validation
- This patch release tightens the public `v0.3` surface; it does not introduce a new `v0.4` product path

## Next steps

- Publish the refreshed guide and update entries through `autorelease`
- Add a public downloadable sample deck once the release asset is hosted
- Move broader new feature work to the `v0.4` line instead of widening the stabilized `v0.3` homepage contract
