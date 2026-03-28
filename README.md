# autoreport

Autoreport is a structured report automation project for turning well-defined
input files into presentation-ready outputs. The long-term direction includes
AI-assisted workflows, but the near-term v0.3 direction is a template-aware
PowerPoint autofill engine that fills user-owned templates instead of
inventing new slide designs. The current v0.2.1 work focuses on a deterministic
weekly report pipeline with both CLI and web-demo entry points.

## Why this project exists

Many teams already know what they want their recurring reports to say, but they
still spend too much time rebuilding the same slide decks by hand. Autoreport
aims to make those reports reproducible, template-driven, and easy to automate.

## Planned CLI usage

```bash
autoreport generate examples/weekly_report.yaml --output output/weekly_report.pptx
```

The CLI validates the YAML input, shapes it into a fixed weekly slide template,
and writes a `.pptx` presentation.

## Planned web demo usage

```bash
uvicorn autoreport.web.app:app --host 0.0.0.0 --port 8000
```

The web demo accepts pasted weekly report YAML, validates it through the same
core pipeline used by the CLI, and returns a generated `.pptx` for download.

## Data handling

Autoreport is designed as a generation engine, not a storage service.

By default, submitted YAML content is processed only to validate the request and
generate the requested `.pptx` output. The generated file is intended for
immediate download and cleanup, and the default web demo flow does not retain
submitted document bodies or generated presentations after request handling.

Because the source code is public, anyone can modify and self-host the project
with different storage behavior. That is outside the default behavior and not
the intended operating policy of this project.

## Roadmap

- v0.1: Deterministic weekly-report CLI with YAML validation and `.pptx` output.
- v0.2: Public web demo plus core hardening for template compatibility and errors.
- v0.3: Template-aware autofill for user-owned PowerPoint templates, fit/spill
  policies, and diagnostics for layout safety.
- v0.4: Optional AI-assisted text shaping, richer layout support, and broader
  workflow automation on top of the template-aware engine.
