# autoreport

Autoreport is a structured report automation project for turning well-defined
input files into presentation-ready outputs. The long-term direction includes
AI-assisted workflows, but the current v0.1 implementation is deterministic and
focused on generating weekly report slide decks from YAML.

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

## Roadmap

- v0.1: Deterministic weekly-report CLI with YAML validation and `.pptx` output.
- v0.2: Richer slide layouts, branding support, and metrics visualizations.
- v0.3: AI-assisted content drafting on top of the structured pipeline.
- v0.4: Web demo, workflow polish, and broader output automation.
