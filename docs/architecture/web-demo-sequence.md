# Web Demo Sequence

This diagram focuses on the current web flow.
It shows the user-facing app path first and then the shared compile/generate
behavior reused by the developer-facing debug app.

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant App as "FastAPI user app"
    participant API as "shared compile/generate routes"
    participant Loader as "parse_yaml_text"
    participant Normalize as "materialize_authoring_payload"
    participant Compile as "materialize_report_payload"
    participant Generator as "generate_report_from_mapping"

    User->>Browser: Open user app
    Browser->>App: GET /
    App-->>Browser: starter-manual HTML + prompted YAML
    opt Bundled screenshot previews
        Browser->>App: GET /starter-assets/{filename}
        App-->>Browser: built-in screenshot file
    end

    User->>Browser: Keep or edit the starter manual YAML
    opt Replace bundled visuals or add new ones
        User->>Browser: Upload image files
        Browser-->>User: refs stay available in the Image Uploads panel
    end

    User->>Browser: Click Generate PPTX
    Browser->>API: POST /api/generate { payload_yaml, image_manifest, uploads }
    API->>Loader: parse_yaml_text(payload_yaml)
    Loader-->>API: raw mapping
    API->>Generator: generate_report_from_mapping(raw_data, image_refs, output_path)
    Generator-->>API: generated .pptx
    API-->>Browser: 200 FileResponse attachment autoreport_demo.pptx
    Browser-->>User: download begins

    alt YAML parse error
        Loader-->>API: yaml.YAMLError
        API-->>Browser: 400 JSON error_type=yaml_parse_error
    else validation error
        Normalize-->>API: ValidationError
        API-->>Browser: 422 JSON error_type=validation_error
    else internal error
        Generator-->>API: unexpected exception
        API-->>Browser: 500 JSON error_type=internal_error
    end
```

The debug app still reuses the same `/api/compile` and `/api/generate` logic.
Its difference is the HTML surface, not the execution path, and it is the place
where compile/runtime inspection remains explicit.

## Inspection points

- `GET /` in `autoreport/web/app.py` is the simplified starter-manual user flow.
- `GET /starter-assets/{filename}` exposes only the bundled built-in screenshots used by that starter.
- `GET /` in `autoreport/web/debug_app.py` is the developer-facing inspection flow.
- `POST /api/compile` accepts multipart form data, not raw JSON, and is primarily surfaced by the debug app.
- `POST /api/generate` also accepts multipart form data and returns a download.
- Temporary files are cleaned up after requests complete.

## Source of truth

- `autoreport/web/app.py`
- `autoreport/web/debug_app.py`
- `autoreport/template_flow.py`
- `autoreport/engine/generator.py`
- `tests/test_web_app.py`
- `tests/test_web_debug_app.py`
