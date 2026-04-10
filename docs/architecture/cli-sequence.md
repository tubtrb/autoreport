# CLI Sequence

This diagram shows the current happy path for `autoreport generate ...` plus the main user-visible failure buckets enforced by the CLI tests.

```mermaid
sequenceDiagram
    participant User
    participant CLI as "cli.main"
    participant Generator as "generate_report"
    participant Loader as "load_yaml"
    participant Payload as "materialize_report_payload"
    participant Template as "content blocks + fill plan"
    participant Writer as "PowerPointWriter.write_fill_plan"
    participant FS as "Filesystem"

    User->>CLI: Run generate command
    CLI->>Generator: generate_report(ReportRequest)
    Generator->>Loader: load_yaml(source_path)
    Loader->>FS: Read YAML file
    FS-->>Loader: YAML text
    Loader-->>Generator: raw mapping
    Generator->>Writer: load template or default presentation
    Generator->>Payload: materialize_report_payload(raw_data, contract)
    Payload-->>Generator: ReportPayload
    Generator->>Template: build content blocks and fill plan
    Template-->>Generator: profiled template + planned slides
    Generator->>Writer: write_fill_plan(presentation, output_path, fill_plan)
    Writer->>FS: Save generated PPTX
    Writer-->>Generator: output_path
    Generator-->>CLI: output_path
    CLI-->>User: stdout success message and exit code 0

    alt known user-facing failure
        Loader-->>CLI: FileNotFoundError or yaml.YAMLError or OSError
        Generator-->>CLI: ValidationError or template or output exception
        CLI-->>User: stderr message and exit code 1
    else unexpected failure
        Generator-->>CLI: unexpected exception
        CLI-->>User: generic internal error and exit code 2
    end
```

## CLI failure mapping

| Failure source | User-visible outcome |
| --- | --- |
| Missing report file | `Report file not found: ...` and exit `1` |
| YAML parse failure | `Failed to parse YAML: ...` and exit `1` |
| Validation failure | `Report validation failed.` plus one line per error and exit `1` |
| Missing template | `Template file not found: ...` and exit `1` |
| Invalid template file | `Invalid PowerPoint template file: ...` and exit `1` |
| Unreadable template file | `Could not read template file: ...` and exit `1` |
| Incompatible template | compatibility message and exit `1` |
| Output write failure | `Could not write report file: ...` and exit `1` |
| Unexpected exception | `An unexpected internal error occurred.` and exit `2` |

## Inspection points

- The CLI is responsible for argument parsing and failure-to-message mapping, not schema logic.
- `ReportRequest` carries `source_path`, optional `output_path`, optional `template_path`, and `template_name`.
- The default output path is `output/<source-stem>.pptx` when `--output` is omitted.
- Narrow CLI verification lives in `tests.test_cli`.

## Source of truth

- `autoreport/cli.py`
- `autoreport/models.py`
- `autoreport/engine/generator.py`
- `tests/test_cli.py`
