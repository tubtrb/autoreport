# User Guide

Current version: `v0.2.1`

This guide reflects the current implementation of Autoreport on the active branch. At this stage, Autoreport validates a structured weekly report YAML input and turns it into a PowerPoint presentation. The same core pipeline is available through both the CLI and the English homepage-backed web demo.

For version-specific changes, see the release notes.

## What is Autoreport?

Autoreport is a structured reporting tool for turning well-defined inputs into presentation-ready outputs. Instead of rebuilding the same weekly deck by hand, you provide a fixed YAML input, validate it against the current schema, and generate a `.pptx` file through a deterministic pipeline.

## What the current version can do

- Validate a weekly report YAML input
- Return clear parsing and validation errors
- Generate a PowerPoint presentation for the current weekly report format
- Reuse a compatible PowerPoint template through the CLI
- Generate a default output path automatically when `--output` is omitted
- Run the same report-generation flow through the homepage/web demo

The current report output uses a fixed five-slide structure:

- Title
- Highlights
- Metrics
- Risks
- Next Steps

## Basic usage

Autoreport currently supports Python `3.10+`.

### CLI

Use the CLI when you want to generate a report from a local YAML file.

```bash
autoreport generate examples/weekly_report.yaml --output output/weekly_report.pptx
```

Available CLI options:

- `--output`: path to the generated `.pptx` file
- `--template`: optional PowerPoint template path

If `--output` is not provided, the default output path is:

```text
output/<input-file-name>.pptx
```

### Homepage / web demo

Use the web demo when you want to paste YAML into the homepage and download a generated `.pptx` directly from the browser.

```bash
uvicorn autoreport.web.app:app --host 0.0.0.0 --port 8000
```

After starting the server, open the homepage, click `Load Example` or paste your own YAML, then click `Generate PPTX`. On the current branch, the success state changes to `Generation complete. Your download should begin shortly.` and the file is downloaded as `weekly_report.pptx`.

## Sample generated PPTX

Before publishing this guide, upload the sample deck and the demo screenshot to WordPress Media and replace the placeholder URLs below.

- Sample output: [Download sample weekly report deck](REPLACE_WITH_PUBLIC_PPTX_URL)
- Demo screenshot:

![Autoreport web demo](REPLACE_WITH_PUBLIC_IMAGE_URL)

<!-- Local working screenshot asset: docs/posts/guide-image-v0.2.1/image.png -->

## Verification on the current branch

The current branch was verified with the web contract tests and real browser smoke checks.

- `.\venv\Scripts\python.exe -m unittest tests.test_web_app` passed
- The homepage loaded successfully in both `msedge` and `chrome`
- The demo completed the sample flow and triggered a `weekly_report.pptx` download

## Supported input structure

The current version supports the weekly report schema only.

Supported top-level fields:

- `title`
- `team`
- `week`
- `highlights`
- `metrics`
- `risks`
- `next_steps`

The `metrics` object currently supports these fields:

- `tasks_completed`
- `open_issues`

## Current limitations

- Only the weekly report format is supported
- Additional top-level fields are not accepted
- The current metrics structure is intentionally narrow
- Template support is available, but templates must remain compatible with the weekly report layout
- The homepage/web demo is currently a lightweight generation surface, not a full document management system

Autoreport is currently focused on making recurring weekly reporting reproducible, predictable, and easy to run through either the CLI or the homepage-based web demo.
