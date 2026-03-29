# Generation Flow

This flowchart shows how input changes shape as it moves through the current weekly report pipeline.
It is useful when you need to inspect where a bug belongs: input loading, schema validation, context shaping, or PowerPoint writing.

```mermaid
flowchart TD
    CLIIN["CLI YAML file path"] --> FILELOAD["load_yaml(path)"]
    WEBIN["Web JSON payload with report_yaml"] --> TEXTLOAD["parse_yaml_text(text)"]

    FILELOAD --> RAW["Raw YAML mapping"]
    TEXTLOAD --> RAW

    RAW --> VALIDATE["validate_report(data)"]
    VALIDATE --> REPORT["Validated WeeklyReport"]
    REPORT --> BLOCKS["build_weekly_report_content_blocks(report)"]
    BLOCKS --> TEMPLATE["Load template or default presentation"]
    TEMPLATE --> PROFILE["profile_weekly_template(...)"]
    PROFILE --> PLAN["build_weekly_report_fill_plan(...)"]
    PLAN --> FIT["fit / shrink / spill decisions"]
    FIT --> CLEAR["Clear seed slides while keeping theme"]
    CLEAR --> BUILD["Write planned slides into profiled placeholders"]
    BUILD --> SAVE["Save PowerPoint output"]
    SAVE --> OUTFILE["weekly_report.pptx"]
```

The pipeline is intentionally narrow.
Only the entry step changes between CLI and web.
After raw data exists, the current flow is shared and deterministic.

## Inspection points

- The validator is the boundary between untrusted input and typed weekly report data.
- The weekly template helper now produces semantic content blocks and a fill plan instead of only a fixed slide-context dict.
- The writer owns template loading, seed-slide removal, and file output.
- Template profiling and fit/spill planning happen before slides are written.
- The current pipeline does not branch by `report_type` or alternate template name.

## Source of truth

- `autoreport/loader.py`
- `autoreport/validator.py`
- `autoreport/templates/weekly_report.py`
- `autoreport/engine/generator.py`
- `autoreport/outputs/pptx_writer.py`
- `tests/test_generator.py`
- `tests/test_pptx_writer.py`
