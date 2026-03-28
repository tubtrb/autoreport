# Web Contract

## Routes

- `GET /` returns the single-page demo HTML.
- `GET /healthz` returns `{"status": "ok"}`.
- `POST /api/generate` accepts JSON with `report_yaml`.

## Successful Generation

- The endpoint parses YAML with `parse_yaml_text(...)`.
- It writes the report into a temporary directory.
- It returns a `FileResponse` with media type `application/vnd.openxmlformats-officedocument.presentationml.presentation`.
- The attachment filename is `weekly_report.pptx`.

## Error Behavior

- YAML parse error -> `400`, `error_type="yaml_parse_error"`
- Validation error -> `422`, `error_type="validation_error"`, plus `errors`
- Unexpected failure -> `500`, `error_type="internal_error"`

## Current HTML Notes

- The page is rendered from the Python source, not a separate template file.
- `tests/test_web_app.py` currently asserts literal HTML strings from `autoreport/web/app.py`.
- Some current page copy shows encoding artifacts in source/tests; treat them as existing contract unless intentionally fixing both together.
