## Autoreport v0.2.1 Release Notes

Release date: `2026-03-28`

Autoreport `v0.2.1` extends the deterministic weekly-report pipeline with a public web demo and clearer release-facing packaging. The current branch now exposes an English homepage flow where users can paste YAML, load a sample weekly report, and download a generated PowerPoint deck directly from the browser.

## Included in this release

- Deterministic weekly report generation through both the CLI and the web demo
- English public demo page with a single-screen YAML-to-PPTX workflow
- Shared validation and generation pipeline between the CLI and the homepage
- Download response from the web demo as `weekly_report.pptx`
- Clearer current-branch release verification using focused tests and browser smoke checks

## Basic usage

CLI:

```bash
autoreport generate examples/weekly_report.yaml --output output/weekly_report.pptx
```

Web demo:

```bash
uvicorn autoreport.web.app:app --host 0.0.0.0 --port 8000
```

On the homepage, click `Load Example` or paste your own YAML and then select `Generate PPTX`.

## Verification on the current branch

This release note is based on the current workspace state rather than a tagged public deployment.

- `.\venv\Scripts\python.exe -m unittest tests.test_web_app` passed
- The homepage loaded successfully in both `msedge` and `chrome`
- The sample flow completed in both browsers and triggered a `weekly_report.pptx` download
- The current browser console issue observed during smoke testing was a non-blocking `favicon.ico` `404`

## Current scope

The current release remains intentionally narrow.

- Only the weekly report schema is supported
- The current metrics structure is limited to `tasks_completed` and `open_issues`
- Template support is available, but templates must stay compatible with the weekly report layout
- The web demo is a lightweight generation surface rather than a full reporting workspace

## Next

The next layer of work is expected to focus on release polish rather than a brand-new generation model.

- Public deployment and homepage linking
- Better documentation flow for WordPress publishing
- Curated sample deck and screenshot assets for external readers
- Future layout, branding, and richer reporting surfaces beyond the current weekly template
