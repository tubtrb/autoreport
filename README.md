# autoreport

Autoreport is a structured report automation project for turning well-defined
input files into presentation-ready outputs. The long-term direction includes
AI-assisted workflows, but v0.1 is intentionally deterministic and focused on a
clean CLI foundation for generating weekly report slides from YAML.

## Why this project exists

Many teams already know what they want their recurring reports to say, but they
still spend too much time rebuilding the same slide decks by hand. Autoreport
aims to make those reports reproducible, template-driven, and easy to automate.

## Planned CLI usage

```bash
autoreport generate examples/weekly_report.yaml
```

The command shape is in place now; report loading and PowerPoint generation
will be implemented incrementally in later tasks.

## Roadmap

- v0.1: Project scaffold, CLI shape, report models, and module boundaries.
- v0.2: YAML loading and schema validation for weekly report inputs.
- v0.3: PowerPoint template binding and `.pptx` generation.
- v0.4: Workflow hardening, testing, and extension points for future automation.
