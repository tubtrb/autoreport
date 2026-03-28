# PPTX Pipeline

## Data Flow

- `generate_report(request)` computes the output path, loads YAML, and delegates to `generate_report_from_mapping(...)`.
- `generate_report_from_mapping(...)` loads a template or default presentation, validates the raw mapping, profiles the template, builds content blocks, creates a fill plan, and writes the deck.
- `PowerPointWriter.write_fill_plan(...)` clears seed slides, writes planned slides, and saves the output file.

## Current Slide Structure

- The current weekly flow still starts with title, highlights, metrics, risks, and next steps.
- Long sections can now spill into continuation slides such as `Highlights (cont.)`.

## Template Assumptions

- Layout index `0` is the current title-layout baseline.
- Layout index `1` is the current body-layout baseline.
- Each profiled layout must provide a title placeholder and one primary text placeholder.
- Placeholder selection is placeholder-first and currently prefers the largest non-title text placeholder.

## Error Surfaces

- Missing template file -> `TemplateNotFoundError`
- Invalid `.pptx` template file -> `TemplateLoadError`
- Unreadable template path -> `TemplateReadError`
- Missing required layouts/placeholders -> `TemplateCompatibilityError`
- Output save failure -> `OutputWriteError`

## Diagnostics

- `font-shrink`: content fit only after reducing font size
- `overflow-spill`: content continued onto another slide
- `out-of-bounds-risk`: one item may still exceed the safe slot budget
- `font-substitution-risk`: user template does not pin a font face for a profiled slot
