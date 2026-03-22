# Weekly Report Schema

## Required Keys

- `title`: non-empty string
- `team`: non-empty string
- `week`: non-empty string
- `highlights`: list with at least one non-empty string
- `metrics`: object with required integer keys
- `risks`: list with at least one non-empty string
- `next_steps`: list with at least one non-empty string

## Metrics

- Allowed keys:
  - `tasks_completed`
  - `open_issues`
- Values must be integers greater than or equal to `0`.
- Boolean values are rejected even though Python treats `bool` as a subtype of `int`.

## Rejected Fields

- `report_type` is explicitly rejected by the current validator.
- Any unexpected top-level key is rejected.
- Any unexpected metric key is rejected.

## Observable Behavior

- `load_yaml` returns raw parsed mappings and does not validate schema.
- `parse_yaml_text` parses YAML text directly and may raise `yaml.YAMLError`.
- `validate_report` trims strings and list items before building `WeeklyReport`.
- Validation errors are collected and surfaced in a stable order locked by tests.
- The current validator error for `report_type` still says `Field 'report_type' is not supported in v0.1.`.
