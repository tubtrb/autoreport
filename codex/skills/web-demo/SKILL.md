---
name: web-demo
description: Handle the FastAPI demo app, public HTML surface, generation API behavior, and web-facing tests for autoreport.
---

# Web Demo

## Overview

Use this skill for `autoreport/web/app.py`, `autoreport/web/debug_app.py`,
the FastAPI routes, the embedded HTML/JavaScript, and the tests that lock web behavior.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/web-contract.md`.
- If the task affects template selection, contract display, or template-driven generation flow, also read:
  - `../../../docs/architecture/template-aware-autofill-engine.md`
  - `../../../docs/architecture/web-surface-split.md`
  - `../../../docs/architecture/v0.3-template-workstreams.md`
- Read `../../../autoreport/web/app.py`.
- Read `../../../autoreport/web/debug_app.py` when the task touches debug workflows or when the product/debug surface split matters.
- Read `../../../tests/test_web_app.py`.
- Read `../../../tests/test_web_debug_app.py` when the task touches the debug app.
- Read `../../../autoreport/engine/generator.py`, `../../../autoreport/loader.py`, and `../../../autoreport/validator.py` if endpoint behavior changes.

## Workflow

1. Preserve route contracts.
- Keep `/` in `autoreport/web/app.py` as the user-facing HTML surface.
- Keep `/` in `autoreport/web/debug_app.py` as the developer-facing debug HTML surface.
- Keep `/healthz` as the lightweight health endpoint.
- Keep `/api/compile` as the authoring-to-runtime preview route shared by both web apps.
- Keep `/api/generate` as the form-data-in, PPTX-or-JSON-out generation route shared by both web apps unless the task explicitly changes the API.

2. Reuse the core pipeline.
- Keep YAML parsing, validation, and PowerPoint generation delegated to shared core modules.
- Do not duplicate schema rules inside the web layer.
- The debug app may expose more developer controls, but it should not fork the compile/generate execution path away from the user app.

3. Keep web error payloads consistent.
- Preserve the current JSON shape with `error_type`, `message`, and optional `errors`.
- Preserve status code mapping unless the task intentionally changes the contract.

4. Treat current HTML copy as tested behavior.
- The user app HTML has literal strings locked by `tests/test_web_app.py`.
- The debug app HTML has literal strings locked by `tests/test_web_debug_app.py`.
- If fixing copy or encoding artifacts, update the tests intentionally in the same change.

5. Keep privacy and cleanup behavior.
- Do not persist pasted YAML content.
- Preserve temporary directory cleanup after downloads and error cases.

## Current Constraints

- Both web apps disable OpenAPI/docs routes.
- Successful `/api/generate` responses return a `.pptx` attachment named `autoreport_demo.pptx`.
- YAML parse failures return `400`.
- Validation failures return `422`.
- Unexpected internal failures return `500`.

## Current Design Frame

Treat this section as living web-surface guidance for the `v0.3` direction.
If the template-driven user flow changes, update this skill and the paired
architecture docs together when practical.

The intended web flow is:

1. in the user app, the user starts from one built-in website manual example that already includes the AI prompt comments at the top, edits that YAML directly, keeps the draft text-first, and generates the deck
2. the user app should stay minimal and avoid contract/debug panes unless the design is intentionally expanded again
3. in the debug app, a developer can inspect the full contract, normalized `authoring_payload`, compiled `report_payload`, and upload refs in parallel panes
4. both apps still validate and generate through the same shared routes and core pipeline

Current design expectations:

- the user app should stay single-flow and user-facing rather than becoming a manual slide-builder
- the public user app should hide image-upload controls and reject image-backed drafts with the standard validation error shape
- the debug app is the right place for extra panes, debug controls, and internal inspection helpers
- the debug app may still keep upload inspection so image-backed drafts remain testable outside the default public surface
- template inspection and compiled runtime debugging belong primarily to the debug app, not the default user app
- the web layer should reuse shared contract-export and validation code instead of re-implementing schema rules
- the homepage should default to one editable starter example rather than an AI prompt package or a manual builder workflow
- the default starter should keep the AI prompt comments at the top of the YAML so the page always begins from one self-contained editable block
- the default starter should stay text-first for the hosted public web flow
- the default starter should act as a practical website manual, not just filler copy
- compiled runtime payload inspection belongs primarily to the debug app and only secondarily to the user app
- error payloads for template-driven validation should stay consistent with the existing web error shape
- if contract download or skeleton generation is added, it should be covered by web tests in the same change

## Output Contract

- State which app surface changed: user app, debug app, or shared API route.
- Cite `tests/test_web_app.py` and/or `tests/test_web_debug_app.py` when describing HTML or API behavior.
