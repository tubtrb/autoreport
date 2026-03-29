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

    User->>Browser: Keep or edit the starter manual YAML
    opt Draft asks for images
        Browser->>API: POST /api/compile or /api/generate with image-backed YAML
        API-->>Browser: 422 JSON validation_error
    end

    User->>Browser: Click Generate PPTX
    Browser->>API: POST /api/generate { payload_yaml, image_manifest=[] }
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
Its difference is the HTML surface plus a public-app guardrail: the default user
app rejects image-backed drafts, while the debug app remains the place where
compile/runtime inspection and upload-backed testing stay explicit.

## Inspection points

- `GET /` in `autoreport/web/app.py` is the simplified starter-manual user flow.
- `GET /` in `autoreport/web/debug_app.py` is the developer-facing inspection flow.
- `POST /api/compile` accepts multipart form data, not raw JSON, and is primarily surfaced by the debug app.
- `POST /api/generate` also accepts multipart form data and returns a download.
- The public app path now keeps `image_manifest` empty and rejects image-backed payloads.
- Temporary files are cleaned up after requests complete.

## Source of truth

- `autoreport/web/app.py`
- `autoreport/web/debug_app.py`
- `autoreport/template_flow.py`
- `autoreport/engine/generator.py`
- `tests/test_web_app.py`
- `tests/test_web_debug_app.py`
