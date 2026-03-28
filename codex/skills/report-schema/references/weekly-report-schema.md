# Contract And Payload Validation

## Public Contract Shapes

- `template_contract` documents the built-in or inspected template patterns and slots.
- `report_content` is the AI-facing draft contract that another model should fill.
- `authoring_payload` is the normalized public authoring contract.
- `report_payload` carries the actual title slide, contents setting, and per-slide content.
- The built-in public examples live at:
  - `examples/autoreport_editorial_template_contract.yaml`
  - `examples/autoreport_editorial_report_content.yaml`
  - `examples/autoreport_editorial_authoring_payload.yaml`
  - `examples/autoreport_editorial_report_payload.yaml`

## Required Payload Fields

- `payload_version`
- `template_id`
- `title_slide.title`
- `title_slide.subtitle`
- `slides`

## Slide Kinds

- `text`
- `metrics`
- `text_image`

Each kind carries its own required fields, and slot overrides must match the
active template contract.

For AI-facing `report_content` drafts, `kind` is optional when `pattern_id`
already maps to a template pattern. The normalization path should prefer the
active `template_contract` over hardcoded user input whenever the draft already
names a valid pattern.

## Observable Behavior

- `load_yaml` returns raw parsed mappings and does not validate schema.
- `parse_yaml_text` accepts either plain YAML or one fenced `yaml` code block and may raise `yaml.YAMLError`.
- Mixed AI output that splits one YAML document across plain text and a later fenced block should be treated as invalid broken draft output.
- `report_content` should derive slide kind from a valid `pattern_id` when possible, and truncated or unknown `pattern_id` values should surface as contract errors instead of unrelated internal-field errors.
- `validate_report` trims strings and list items before building the current validated payload model.
- Validation errors are collected and surfaced in a stable order locked by tests.
- Legacy error strings that still mention earlier versions should be treated as compatibility debt unless the tests intentionally change them.
