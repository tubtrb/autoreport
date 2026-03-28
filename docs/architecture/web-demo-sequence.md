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
    App-->>Browser: AI-draft-first HTML

    User->>Browser: Copy AI package to another AI
    User->>Browser: Paste returned report_content draft

    opt Optional compile preview
        Browser->>API: POST /api/compile { payload_yaml, image_manifest, uploads }
        API->>Loader: parse_yaml_text(payload_yaml)
        Loader-->>API: raw mapping
        API->>Normalize: normalize report_content -> authoring_payload
        Normalize-->>API: authoring payload + hints
        API->>Compile: compile to report_payload
        Compile-->>API: compiled runtime payload
        API-->>Browser: JSON payload_kind + normalized_authoring_yaml + compiled_yaml
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

The debug app reuses the same `/api/compile` and `/api/generate` logic.
Its difference is the HTML surface, not the execution path.

## Inspection points

- `GET /` in `autoreport/web/app.py` is the simplified user-facing flow.
- `GET /` in `autoreport/web/debug_app.py` is the developer-facing inspection flow.
- `POST /api/compile` accepts multipart form data, not raw JSON.
- `POST /api/generate` also accepts multipart form data and returns a download.
- Temporary files are cleaned up after requests complete.

## Source of truth

- `autoreport/web/app.py`
- `autoreport/web/debug_app.py`
- `autoreport/template_flow.py`
- `autoreport/engine/generator.py`
- `tests/test_web_app.py`
- `tests/test_web_debug_app.py`
