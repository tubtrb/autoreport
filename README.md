# autoreport

Autoreport is a template-contract-first PPTX generation engine.
It inspects a PowerPoint template, exports the fillable contract, accepts a
structured payload that another AI or a human can fill, and returns an editable
PowerPoint deck.

The current built-in baseline is `autoreport_editorial`, an Autoreport-owned
editorial template designed for fast contract-first generation.

## Product flow

1. inspect a template and export its contract
2. scaffold or fill a `report_payload`
3. generate an editable `.pptx`

Autoreport does not call an LLM during generation.
The AI-friendly layer is the exported contract and payload structure, so deck
generation stays deterministic and near-instant.

## Quickstart

The current release surface is anchored to the CLI flows exercised in
`tests/test_cli.py` and the web-demo flows exercised in `tests/test_web_app.py`.
Use the CLI when you want to inspect a template contract, scaffold a payload,
or generate a deck from disk-backed files.

Inspect the built-in editorial template contract:

```bash
autoreport inspect-template --built-in autoreport_editorial --output output/template_contract.yaml
```

Scaffold a starter payload from the exported contract:

```bash
autoreport scaffold-payload output/template_contract.yaml --output output/report_payload.yaml
```

Review the scaffolded payload, then generate a deck:

```bash
autoreport generate output/report_payload.yaml --output output/autoreport_demo.pptx
```

The built-in editorial scaffold can include a `text_image` slide.
If you keep that slide, replace its `image.ref` with a real `image.path` or
remove the slide before CLI generation while you are still drafting content.

Inspect and generate against a user-owned `.pptx` template:

```bash
autoreport inspect-template --template path/to/template.pptx --output output/template_contract.yaml
autoreport generate output/report_payload.yaml --template path/to/template.pptx --output output/custom_deck.pptx
```

See `docs/release-readiness.md` for a short verification checklist that stays
within the currently implemented and tested release scope.

## Web demo

Run the local demo:

```bash
uvicorn autoreport.web.app:app --host 0.0.0.0 --port 8000
```

The web demo currently targets the built-in editorial template only.
It shows the contract, lets you edit the payload YAML, supports uploaded image
refs such as `image_1`, and returns a generated `.pptx` for immediate download.
Arbitrary PowerPoint template upload is currently a CLI-only path.

## Example documents

- `examples/autoreport_editorial_template_contract.yaml`: built-in editorial contract export
- `examples/autoreport_editorial_report_payload.yaml`: built-in editorial payload reference, including the `text_image` example that uses `image_1`

## Data handling

Autoreport is designed as a generation engine, not a storage service.

Submitted payloads are processed only long enough to validate the request and
generate the requested `.pptx`. The default web demo flow cleans up temporary
generated files after download and does not retain payload contents by default.

## Current Release Boundaries

- Contract inspection, payload scaffolding, and PPTX generation are available through the CLI.
- The public web demo covers the built-in editorial template, pasted payload YAML, image refs, and immediate PPTX download.
- Generation remains deterministic and local to Python plus `python-pptx`; there is no server-side LLM call in the generation path.
- Version bumping, tagging, and release publication are intentionally handled outside this branch.
