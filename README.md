# autoreport

Autoreport is a template-contract-first PPTX generation engine.
It inspects a PowerPoint template, exports the fillable contract, accepts either
a high-level `report_content` draft from another AI or a ready-made
`authoring_payload`, compiles
that into the runtime `report_payload`, and returns an editable PowerPoint deck.

The current built-in baseline is `autoreport_editorial`, an Autoreport-owned
editorial template designed for fast contract-first generation.

## Product flow

1. inspect a template and export its contract
2. ask another AI to draft `report_content`, or scaffold/fill an `authoring_payload`
3. optionally compile it into a `report_payload` for debugging
4. generate an editable `.pptx`

Autoreport does not call an LLM during generation.
The AI-friendly layer is the exported contract plus the public draft surfaces
`report_content` and `authoring_payload`, so deck generation stays deterministic
and near-instant.

When another AI writes `report_content`, the safest response shape is:

1. return exactly one fenced `yaml` code block
2. keep the top-level key as `report_content`
3. do not write prose before or after the code block
4. do not split the YAML across multiple code blocks
5. choose `pattern_id` values only from the exported `template_contract`
6. let the number of `slides` entries determine the deck length

## Quickstart

The current release surface is anchored to the CLI flows exercised in
`tests/test_cli.py` and the web-demo flows exercised in `tests/test_web_app.py`.
Use the CLI when you want to inspect a template contract, scaffold a payload,
or generate a deck from disk-backed files.

Inspect the built-in editorial template contract:

```bash
autoreport inspect-template --built-in autoreport_editorial --output output/template_contract.yaml
```

Scaffold a starter authoring payload from the exported contract:

```bash
autoreport scaffold-payload output/template_contract.yaml --output output/authoring_payload.yaml
```

Compile the authored input into the runtime `report_payload` when you want to
inspect the exact execution payload. `compile-payload` also accepts a
`report_content` draft and normalizes it first:

```bash
autoreport compile-payload output/authoring_payload.yaml --output output/report_payload.yaml
```

Review the authored input, then generate a deck:

```bash
autoreport generate output/authoring_payload.yaml --output output/autoreport_demo.pptx
```

The default CLI scaffold is compile-ready and text-first.
When you want image-backed slides, add `assets.images[*].path` values in the
CLI or use the debug web app path with `assets.images[*].ref`.

Inspect and generate against a user-owned `.pptx` template:

```bash
autoreport inspect-template --template path/to/template.pptx --output output/template_contract.yaml
autoreport generate output/authoring_payload.yaml --template path/to/template.pptx --output output/custom_deck.pptx
```

See `docs/release-readiness.md` for a short verification checklist that stays
within the currently implemented and tested release scope.

For Ubuntu EC2 hosting, see `docs/deployment/aws-ec2.md` and the reusable
assets under `deploy/aws-ec2/`.

## Web demo

Run the local demo:

```bash
python -m autoreport.web.serve public --host 0.0.0.0 --port 8000
```

On Windows from the repo root, the shortest local command is:

```powershell
.\run-public.cmd
```

The wrapper above is the supported local launch path because it shuts down
cleanly on `Ctrl-C` without printing the `uvicorn`/`asyncio` traceback that can
appear on Python 3.14 when using `python -m uvicorn ...` directly.

The web demo opens with the built-in manual procedure starter by default, keeps
the AI prompt comments at the top of the starter YAML, and returns a generated
`.pptx` for immediate download. The public page now focuses on the
screenshot-first manual flow with paired upload and preview rows on the built-in
`autoreport_manual` template.
Slide counts are inferred dynamically from the authored slides list rather than
entered as a separate field.
Arbitrary PowerPoint template upload is currently a CLI-only path.

The user-facing app is intentionally simple:

1. start from the built-in manual procedure starter
2. keep or edit the AI prompt comments at the top of the YAML
3. keep the public homepage focused on the manual screenshot workflow
4. use the paired upload panels and slide preview to align screenshots with each image-bearing slide
5. use the debug app or CLI when the deck needs custom inspection or arbitrary image/template control
6. generate the deck

When you want a developer-facing surface with more panes for contract inspection,
normalization, and compiled runtime debugging, run the separate debug app:

```bash
python -m autoreport.web.serve debug --host 0.0.0.0 --port 8010
```

Or from the repo root on Windows:

```powershell
.\run-debug.cmd
```

## Example documents

- `examples/autoreport_editorial_template_contract.yaml`: built-in editorial contract export
- `examples/autoreport_editorial_report_content.yaml`: AI-facing draft example for another model to fill
- `examples/autoreport_editorial_authoring_payload.yaml`: built-in editorial authoring example, including the `text_image` example that uses `image_1`
- `examples/autoreport_editorial_report_payload.yaml`: compiled runtime payload reference for the built-in editorial template
- `examples/autoreport_manual_template_contract.yaml`: built-in manual contract export for screenshot-first procedure decks
- `examples/autoreport_manual_report_content.yaml`: screenshot-first manual draft example for the built-in public manual starter
- `examples/autoreport_manual_authoring_payload.yaml`: built-in manual authoring starter with alias-based slot values

## Data handling

Autoreport is designed as a generation engine, not a storage service.

Submitted payloads are processed only long enough to validate the request and
generate the requested `.pptx`. The default web demo flow cleans up temporary
generated files after download and does not retain payload contents by default.

## Current Release Boundaries

- Contract inspection, authoring-payload scaffolding, authoring-to-runtime compilation, and PPTX generation are available through the CLI.
- The public web demo covers the built-in manual procedure starter on `autoreport_manual`, pasted `report_content` or `authoring_payload` YAML, paired screenshot upload/preview for manual mode, and immediate PPTX download.
- The default public homepage now leads directly with the manual starter rather than an editorial-first starter selector.
- Generation remains deterministic and local to Python plus `python-pptx`; there is no server-side LLM call in the generation path.
- Versioned release-note, guide, and devlog handoff is prepared locally through `docs/posts/`, while stable standalone public pages are sourced from `docs/pages/`, before syncing into the private `autorelease` repository.
