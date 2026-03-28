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

## CLI

Inspect the built-in editorial template contract:

```bash
autoreport inspect-template --built-in autoreport_editorial
```

Scaffold a starter payload from a saved contract:

```bash
autoreport scaffold-payload examples/autoreport_editorial_template_contract.yaml
```

Generate a deck from a payload file:

```bash
autoreport generate examples/autoreport_editorial_report_payload.yaml --output output/autoreport_demo.pptx
```

Generate against a user-owned `.pptx` template:

```bash
autoreport inspect-template --template path/to/template.pptx --output output/template_contract.yaml
autoreport generate output/report_payload.yaml --template path/to/template.pptx --output output/custom_deck.pptx
```

## Web demo

Run the local demo:

```bash
uvicorn autoreport.web.app:app --host 0.0.0.0 --port 8000
```

The web demo currently targets the built-in editorial template only.
It shows the contract, lets you edit the payload YAML, supports uploaded image
refs such as `image_1`, and returns a generated `.pptx` for immediate download.

## Example documents

- `examples/autoreport_editorial_template_contract.yaml`
- `examples/autoreport_editorial_report_payload.yaml`

## Data handling

Autoreport is designed as a generation engine, not a storage service.

Submitted payloads are processed only long enough to validate the request and
generate the requested `.pptx`. The default web demo flow cleans up temporary
generated files after download and does not retain payload contents by default.

## Roadmap frame

- v0.3: template-aware PPTX autofill, contract export, deterministic fill/spill, and editable deck output
- v0.4: broader workflow automation, richer template patterns, and optional AI-assisted authoring on top of the contract-first engine
