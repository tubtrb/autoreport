# CLI Contract

## Command Shape

- Root program name: `autoreport`
- Current subcommand: `generate`
- Current options:
  - required positional `report_path`
  - optional `--output` / `-o`
  - optional `--template`

## Success Behavior

- The CLI builds a `ReportRequest` and calls `generate_report`.
- Successful generation prints exactly:
  - `Report generated successfully: <output_path>`
- Successful runs exit with code `0`.

## Failure Mapping

- Missing report file -> `Report file not found: <path>` and exit `1`
- Invalid/missing template and template compatibility failures -> specific stderr text and exit `1`
- Output write failure -> `Could not write report file: <path>` and exit `1`
- YAML parse failure -> `Failed to parse YAML: ...` and exit `1`
- Validation failure -> `Report validation failed.` plus one `- ...` line per error and exit `1`
- Unexpected internal exceptions -> `An unexpected internal error occurred.` and exit `2`
