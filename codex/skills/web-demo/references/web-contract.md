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

- `python -m autoreport.web.serve public --host 127.0.0.1 --port 8000`

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

- Start from one built-in editable starter example by default.
- Keep the AI prompt comments at the top of that starter YAML so the page always starts from one self-contained editable block.
- Keep the default public starter focused on the manual screenshot workflow for the current hosted flow.
- Keep one large working input area as the primary surface.
- Treat total slide count as dynamic; infer it from the draft, not from a separate input field.
- Keep the user app minimal: reset the starter example, edit YAML, pair uploads with image-bearing slide previews, and generate.
- The user app may include lightweight add/remove manual slide controls when they edit the existing YAML draft in place instead of becoming a full manual builder.
- The user app may include a lightweight manual draft checker when it catches invalid manual pattern_id choices and numbering issues before generation.
- In manual mode, if a preview is shown, prefer the composed slide result over raw uploaded-image thumbnails.
- Manual slide previews should follow the actual generation fill plan closely enough to reflect continuation slides, slot-level image retention, and fitted text/layout decisions rather than a naive compiled-payload sketch.
- In manual mode, keep screenshot uploads paired with the exact preview row for each image-bearing slide so the controls and composed preview stay horizontally aligned.
- Do not restore the old image-order list or a detached upload column in the user app; only image-bearing slides should show upload controls.
- Keep the upload side compact: avoid repeated instructional paragraphs and use one-line slide summaries so paired rows stay dense and readable.
- Do not restore the old website-intro/editorial starter selector in the user app.
- Avoid helper panes such as template-contract or compiled-runtime inspection in the default user app when they do not directly improve the main flow.
- Avoid full manual slide-by-slide builder controls in the user app.
- A preset gallery is acceptable only when it keeps YAML as the primary working surface and limits manual controls to targeted add/remove actions instead of reorder/replace controls.
- A manual draft checker is acceptable only when it stays rule-focused, surfaces blocking issues before generation, and does not expand into a full compiled-payload inspection pane.
- Make it explicit that image-backed drafts belong in the debug app or CLI rather than the default public page.

## Debug App Contract

Entrypoint:

- `python -m autoreport.web.serve debug --host 127.0.0.1 --port 8010`

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
- It may become the inspection surface for template/prompt robustness workbench outputs such as corpus summaries, failure samples, and targeted reruns.
- High-volume robustness execution across many drafts or templates should live in a CLI or batch runner, not in long-running browser-driven loops inside the debug app.

## Input Contract

Supported draft surfaces for both web apps:

- `report_content`
- `authoring_payload`
- legacy `report_payload`

Expected behavior:

- `report_content` is a high-level AI-facing draft surface.
- `authoring_payload` is the normalized public authoring surface.
- `report_payload` is the compiled runtime surface and remains supported for compatibility.
- When another AI is asked to draft `report_content`, the safest response shape is exactly one fenced `yaml` code block with no prose before or after it.
- In `report_content`, `pattern_id` is the primary layout selector and `kind` is optional when the pattern already exists in the active template contract.
- Plain YAML and one complete fenced `yaml` block are both accepted.
- Mixed outputs that split YAML across unfenced text and a later fenced block should be rejected as broken AI output.
- If an AI returns a truncated or misspelled `pattern_id`, the web layer should surface that contract mismatch clearly instead of leaking an unrelated internal field error.

For image-backed slides:

- The public user app should reject them with the standard validation error shape.
- The debug app may still accept upload refs such as `image_1`, and the CLI may still accept filesystem paths.

## Successful Responses

`POST /api/compile`

- Returns JSON with:
  - `payload_kind`
  - `normalized_authoring_yaml`
  - `compiled_yaml`
  - `slide_count`
  - `required_images`
  - `slide_previews`
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
