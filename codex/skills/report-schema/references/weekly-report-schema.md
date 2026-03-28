# Contract And Payload Validation

## Public Contract Shapes

- `template_contract` documents the built-in or inspected template patterns and slots.
- `report_payload` carries the actual title slide, contents setting, and per-slide content.
- The built-in public examples live at:
  - `examples/autoreport_editorial_template_contract.yaml`
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

## Observable Behavior

- `load_yaml` returns raw parsed mappings and does not validate schema.
- `parse_yaml_text` parses YAML text directly and may raise `yaml.YAMLError`.
- `validate_report` trims strings and list items before building the current validated payload model.
- Validation errors are collected and surfaced in a stable order locked by tests.
- Legacy error strings that still mention earlier versions should be treated as compatibility debt unless the tests intentionally change them.
