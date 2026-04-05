## Autoreport v0.3.0 Release Notes

Release date: `2026-03-29`

Autoreport `v0.3.0` wraps the `v0.3` branch line into one contract-first release surface. The product now centers on template inspection, explicit draft contracts, deterministic PPTX generation, a simplified public web app, a separate debug app, and a private publishing handoff that keeps the public guide and updates pages organized.

## Live service

As of `2026-03-29`, the public release pages and the hosted demo app are available at:

- Release-facing site home: `http://auto-report.org/`
- Release-facing user guide: `http://auto-report.org/guide/`
- Release-facing updates hub: `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`
- Hosted demo app: `http://3.36.96.47/`
- Alternate EC2 hostname: `http://ec2-3-36-96-47.ap-northeast-2.compute.amazonaws.com/`
- Hosted demo health check: `http://3.36.96.47/healthz` returns `{"status":"ok"}`

## What's included in this release

- Template-contract-first CLI flows for `inspect-template`, `scaffold-payload`, `compile-payload`, and `generate`
- Public draft support for `report_content`, normalized `authoring_payload`, and compiled `report_payload`
- Built-in editorial template patterns for text, metrics, and image-backed slides
- Separate user-facing and developer-facing FastAPI apps on top of the same compile/generate routes
- Public web starter flow that now stays text-first for the hosted homepage
- Stable publishing organization for Home `http://auto-report.org/`, User Guide `http://auto-report.org/guide/`, and the Updates hub `http://auto-report.org/%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8/`

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
uvicorn autoreport.web.app:app --host 0.0.0.0 --port 8000
```

On the homepage, edit the built-in starter manual, keep the public draft on text or metrics slides, and select `Generate PPTX`. If the deck needs image-backed slides, move that run to the debug app or the CLI.

## Supported input structure

Autoreport currently exposes these public shapes:

- `template_contract`
- `report_content`
- `authoring_payload`
- `report_payload`

In the current release, `report_content` is the primary AI-facing draft surface, `authoring_payload` is the normalized public authoring surface, and `report_payload` remains the compiled runtime surface.

## Output format

- CLI generation writes an editable `.pptx` to the requested output path
- The web demo returns `autoreport_demo.pptx` as the immediate download filename
- Slide counts are inferred from the authored slides list rather than entered as a separate field

## Verification on the current branch

This release note is based on the current workspace state rather than a tagged public deployment.

- `.\venv\Scripts\python.exe -m unittest tests.test_cli tests.test_loader tests.test_validator tests.test_autofill tests.test_generator tests.test_pptx_writer tests.test_web_app tests.test_web_debug_app` passed
- The public homepage stays text-first and rejects image-backed drafts with a validation error
- The current browser success path downloads `autoreport_demo.pptx`

## Current limitations

- Public web upload of arbitrary external PowerPoint templates is not part of the current demo surface
- The public web app intentionally avoids contract/debug panes and the image-backed slide flow; those remain in the separate debug app and CLI
- The final WordPress publish step still runs from the private `autorelease` repository after validation
- Some deeper internal architecture notes still keep legacy weekly-era wording outside the release-facing docs updated for this release

## Next steps

- Publish the refreshed guide and update entries through `autorelease`
- Add a public downloadable sample deck once the release asset is hosted
- Decide whether the image-backed homepage flow should return after the web contract is hardened further
