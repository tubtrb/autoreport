# PPTX Pipeline

## Data Flow

- `generate_report(request)` computes the output path, loads YAML, and delegates to `generate_report_from_mapping(...)`.
- `generate_report_from_mapping(...)` validates the raw mapping, builds slide context, and calls `PowerPointWriter.write(...)`.
- `PowerPointWriter.write(...)` loads a template or default presentation, checks layout compatibility, clears seed slides, adds slides, and saves the output file.

## Current Slide Structure

- Slide 1: title slide with report title and `team + week` subtitle
- Slide 2: `Highlights`
- Slide 3: `Metrics`
- Slide 4: `Risks`
- Slide 5: `Next Steps`

## Template Assumptions

- Layout index `0` is the title layout.
- Layout index `1` is the bullet/content layout.
- Placeholder index `1` on both layouts must support text.

## Error Surfaces

- Missing template file -> `TemplateNotFoundError`
- Invalid `.pptx` template file -> `TemplateLoadError`
- Unreadable template path -> `TemplateReadError`
- Missing required layouts/placeholders -> `TemplateCompatibilityError`
- Output save failure -> `OutputWriteError`
