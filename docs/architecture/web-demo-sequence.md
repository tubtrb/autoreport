# Web Demo Sequence

This diagram focuses on the current public demo generation path.
It shows both the initial page load and the `POST /api/generate` request that actually produces the download.

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant API as "FastAPI app"
    participant Loader as "parse_yaml_text"
    participant Generator as "generate_report_from_mapping"
    participant Validator as "validate_report"
    participant Template as "content blocks + fill plan"
    participant Writer as "PowerPointWriter.write_fill_plan"

    User->>Browser: Open demo page
    Browser->>API: GET /
    API-->>Browser: HTML demo page

    User->>Browser: Paste YAML and click Generate PPTX
    Browser->>API: POST /api/generate { report_yaml }
    API->>Loader: parse_yaml_text(report_yaml)
    Loader-->>API: raw mapping
    API->>Generator: generate_report_from_mapping(raw_data, output_path)
    Generator->>Writer: load template or default presentation
    Generator->>Validator: validate_report(raw_data)
    Validator-->>Generator: WeeklyReport
    Generator->>Template: build content blocks and fill plan
    Template-->>Generator: profiled template + planned slides
    Generator->>Writer: write_fill_plan(presentation, output_path, fill_plan)
    Writer-->>API: temp weekly_report.pptx
    API-->>Browser: 200 FileResponse attachment
    Browser-->>User: download begins

    alt YAML parse error
        Loader-->>API: yaml.YAMLError
        API-->>Browser: 400 JSON error_type=yaml_parse_error
    else validation error
        Generator-->>API: ValidationError
        API-->>Browser: 422 JSON error_type=validation_error
    else internal error
        Generator-->>API: unexpected exception
        API-->>Browser: 500 JSON error_type=internal_error
    end
```

The web demo creates a temporary output directory for each request and cleans it up after the file response is sent.
It does not persist the submitted YAML as part of the request flow.

## Inspection points

- `GET /` serves a single-page HTML demo with tested literal UI copy.
- `GET /healthz` is a deployment check endpoint and not part of the generation sequence.
- `POST /api/generate` accepts JSON with one field, `report_yaml`.
- The web demo reuses the same generator core as the CLI after YAML becomes a mapping.
- The web surface returns HTTP status codes instead of CLI exit codes.

## Source of truth

- `autoreport/web/app.py`
- `autoreport/loader.py`
- `autoreport/engine/generator.py`
- `tests/test_web_app.py`
