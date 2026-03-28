---
name: web-demo
description: Handle the FastAPI demo app, public HTML surface, generation API behavior, and web-facing tests for autoreport.
---

# Web Demo

## Overview

Use this skill for `autoreport/web/app.py`, the FastAPI routes,
the embedded demo HTML/JavaScript, and the tests that lock web behavior.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/web-contract.md`.
- If the task affects template selection, contract display, or template-driven generation flow, also read:
  - `../../../docs/architecture/template-aware-autofill-engine.md`
  - `../../../docs/architecture/v0.3-template-workstreams.md`
- Read `../../../autoreport/web/app.py`.
- Read `../../../tests/test_web_app.py`.
- Read `../../../autoreport/engine/generator.py`, `../../../autoreport/loader.py`, and `../../../autoreport/validator.py` if endpoint behavior changes.

## Workflow

1. Preserve route contracts.
- Keep `/` as the HTML demo surface.
- Keep `/healthz` as the lightweight health endpoint.
- Keep `/api/generate` as the JSON-in, PPTX-or-JSON-out generation route unless the task explicitly changes the API.

2. Reuse the core pipeline.
- Keep YAML parsing, validation, and PowerPoint generation delegated to shared core modules.
- Do not duplicate schema rules inside the web layer.

3. Keep web error payloads consistent.
- Preserve the current JSON shape with `error_type`, `message`, and optional `errors`.
- Preserve status code mapping unless the task intentionally changes the contract.

4. Treat current HTML copy as tested behavior.
- The demo HTML currently has literal strings locked by `tests/test_web_app.py`.
- If fixing copy or encoding artifacts, update the tests intentionally in the same change.

5. Keep privacy and cleanup behavior.
- Do not persist pasted YAML content.
- Preserve temporary directory cleanup after downloads and error cases.

## Current Constraints

- The web app disables OpenAPI/docs routes.
- Successful `/api/generate` responses return a `.pptx` attachment named `weekly_report.pptx`.
- YAML parse failures return `400`.
- Validation failures return `422`.
- Unexpected internal failures return `500`.

## Current Design Frame

Treat this section as living web-surface guidance for the `v0.3` direction.
If the template-driven user flow changes, update this skill and the paired
architecture docs together when practical.

The intended web flow is:

1. user selects or uploads a template
2. the app shows the required YAML or JSON contract for that template
3. a human or another AI fills the payload
4. the app validates the payload and returns a generated `.pptx`

Current design expectations:

- template inspection and contract display should be product behavior, not hidden diagnostics
- the web layer should reuse shared contract-export and validation code instead of re-implementing schema rules
- if the web surface exposes both weekly and generalized template-driven flows, the distinction should be explicit to the user
- error payloads for template-driven validation should stay consistent with the existing web error shape
- if contract download or skeleton generation is added, it should be covered by web tests in the same change

## Output Contract

- State which route or response contract changed.
- Cite `tests/test_web_app.py` when describing HTML or API behavior.
