# Web Contract

## Web Surface Split

Autoreport now ships two separate FastAPI web surfaces:

- `autoreport/web/app.py`
  Purpose: user-facing app.
  Shape: one primary input flow, minimal controls, optional contract/debug panels.
- `autoreport/web/debug_app.py`
  Purpose: developer-facing debug app.
  Shape: multi-pane inspection surface for contract, normalization, compiled payloads, and upload debugging.

Do not collapse these two surfaces back into one crowded homepage unless the task explicitly redesigns that split.

## User App Contract

Entrypoint:

- `uvicorn autoreport.web.app:app --host 127.0.0.1 --port 8000`

Routes:

- `GET /`
  Returns the user-facing single-page HTML.
- `GET /healthz`
  Returns `{"status": "ok"}`.
- `POST /api/compile`
  Accepts multipart form data with `payload_yaml` plus optional `image_manifest` and uploaded files.
  Used to normalize `report_content` into `authoring_payload` and preview the compiled `report_payload`.
- `POST /api/generate`
  Accepts the same multipart form data and returns the generated `.pptx`.

User-app UI contract:

- Start from an AI-friendly `report_content` prompt by default.
- Keep one large working input area as the primary surface.
- Treat total slide count as dynamic; infer it from the draft, not from a separate input field.
- Keep helper panes optional. Contract view and compiled runtime view may exist, but must stay secondary to the main authoring flow.
- Avoid manual slide-by-slide builder controls in the user app when the intended flow is "ask another AI for N slides, paste, generate."

## Debug App Contract

Entrypoint:

- `uvicorn autoreport.web.debug_app:app --host 127.0.0.1 --port 8010`

Routes:

- `GET /`
  Returns the developer-facing debug HTML.
- `GET /healthz`
  Returns `{"status": "ok"}`.
- `POST /api/compile`
  Same core route contract as the user app.
- `POST /api/generate`
  Same core route contract as the user app.

Debug-app UI contract:

- It is allowed to expose more panes and controls than the user app.
- It should make normalization and compiled payload inspection explicit.
- It should help verify upload refs, pattern choices, and current contract export without changing the shared core API contract.
- It must reuse the same `/api/compile` and `/api/generate` logic as the user app rather than drifting into a separate execution path.

## Input Contract

Supported draft surfaces for both web apps:

- `report_content`
- `authoring_payload`
- legacy `report_payload`

Expected behavior:

- `report_content` is a high-level AI-facing draft surface.
- `authoring_payload` is the normalized public authoring surface.
- `report_payload` is the compiled runtime surface and remains supported for compatibility.

For image-backed slides:

- AI drafts may describe desired visuals inside `slots.image_*`.
- Real image files are supplied later through upload refs such as `image_1` in the web apps or filesystem paths in the CLI.

## Successful Responses

`POST /api/compile`

- Returns JSON with:
  - `payload_kind`
  - `normalized_authoring_yaml`
  - `compiled_yaml`
  - `slide_count`
  - `hints`

`POST /api/generate`

- Returns a `FileResponse`
- media type:
  `application/vnd.openxmlformats-officedocument.presentationml.presentation`
- filename:
  `autoreport_demo.pptx`

## Error Behavior

- YAML parse error -> `400`, `error_type="yaml_parse_error"`
- Validation error -> `422`, `error_type="validation_error"`, plus `errors`
- Unexpected failure -> `500`, `error_type="internal_error"`

Keep this error shape stable across both apps.

## Source Of Truth

- `autoreport/web/app.py`
- `autoreport/web/debug_app.py`
- `tests/test_web_app.py`
- `tests/test_web_debug_app.py`
