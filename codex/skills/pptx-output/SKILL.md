---
name: pptx-output
description: Handle weekly template shaping, generation orchestration, PowerPoint writing, and template compatibility behavior for autoreport outputs.
---

# PPTX Output

## Overview

Use this skill for `autoreport/templates/weekly_report.py`,
`autoreport/engine/generator.py`, `autoreport/outputs/pptx_writer.py`,
and the tests that lock generation and template compatibility behavior.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/pptx-pipeline.md`.
- Read `../../../autoreport/templates/weekly_report.py`.
- Read `../../../autoreport/engine/generator.py`.
- Read `../../../autoreport/outputs/pptx_writer.py`.
- Read `../../../tests/test_generator.py` and `../../../tests/test_pptx_writer.py`.
- If CLI/web error handling changes, inspect `../../../tests/test_cli.py` or `../../../tests/test_web_app.py`.

## Workflow

1. Preserve the current pipeline shape.
- `generate_report` loads YAML and delegates to `generate_report_from_mapping`.
- `generate_report_from_mapping` validates, profiles the template, builds content blocks, creates a fill plan, and writes the `.pptx`.
- Keep orchestration separate from file writing.

2. Keep template context stable.
- `build_weekly_report_content_blocks` expresses the semantic weekly sections.
- `build_weekly_report_fill_plan` maps those sections into template slots and continuation slides.
- Preserve slide ordering and metric labeling unless the task intentionally changes presentation structure.

3. Treat template compatibility as a first-class contract.
- The current weekly profile starts from layout index `0` for the title slide and `1` for the body slide.
- Each profiled layout must expose a title placeholder plus one primary text placeholder.
- Preserve explicit template error types so CLI and web surfaces can map them cleanly.

4. Update tests when slide structure changes.
- Any change to slide count, titles, metric labeling, template assumptions, or error text should update generation/writer tests in the same change.

## Current Constraints

- Supported template name is currently only `weekly_report`.
- Default output path is `output/<source-stem>.pptx` when the caller does not provide one.
- The default writer path uses a fresh `Presentation()` if no template path is supplied.
- Existing slides from a template are cleared before report slides are added.
- The current fit policy prefers the default font size, shrinks as needed, then spills onto continuation slides.
- Diagnostics currently cover font shrink, overflow spill, out-of-bounds risk, and user-template font substitution risk.

## Output Contract

- State the pipeline stage being changed: template profiling, content block shaping, fill planning, diagnostics, compatibility, or file writing.
- Cite generation/writer tests for slide structure and template assumptions.
