---
name: pptx-output
description: Handle template shaping, generation orchestration, PowerPoint writing, and template compatibility behavior for autoreport outputs.
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
- Read `../../../docs/architecture/template-aware-autofill-engine.md`.
- If the task affects versioned branch planning, generalized contracts, or cross-thread ownership, also read `../../../docs/architecture/template-workstreams.md`.
- Read `../../../autoreport/templates/weekly_report.py`.
- Read `../../../autoreport/engine/generator.py`.
- Read `../../../autoreport/outputs/pptx_writer.py`.
- Read `../../../tests/test_autofill.py`, `../../../tests/test_generator.py`, and `../../../tests/test_pptx_writer.py`.
- If CLI/web error handling changes, inspect `../../../tests/test_cli.py` or `../../../tests/test_web_app.py`.

## Workflow

1. Preserve the current pipeline shape.
- `generate_report` loads YAML and delegates to `generate_report_from_mapping`.
- `generate_report_from_mapping` validates, profiles the template, builds content blocks, creates a fill plan, and writes the `.pptx`.
- Keep orchestration separate from file writing.

2. Keep template context stable.
- `build_weekly_report_content_blocks` still carries a legacy name, but it now shapes the semantic contract-driven slide content used by the supported built-in templates.
- `build_weekly_report_fill_plan` maps those sections into template slots and continuation slides.
- Preserve slide ordering and metric labeling unless the task intentionally changes presentation structure.

3. Treat template compatibility as a first-class contract.
- The current template profile dynamically searches the supplied template for a compatible title layout and compatible body layouts instead of assuming fixed indices.
- Title slides may use either a real title placeholder or title-like text placeholders; body slides still need a title slot plus one primary content slot.
- Preserve explicit template error types so CLI and web surfaces can map them cleanly.

4. Update tests when slide structure changes.
- Any change to slide count, titles, metric labeling, template assumptions, or error text should update generation/writer tests in the same change.

## Current Design Frame

Treat this section as living design guidance for the template-aware engine.
If real usage changes the design, update this skill and the paired architecture
docs together when practical.

The intended template-driven flow is:

1. user selects a PowerPoint template
2. the engine profiles that template and exposes the required YAML or JSON contract
3. a human or another AI fills the contract
4. the engine generates a `.pptx` against the selected template

Current design expectations:

- template profiling should move toward explicit contract export, not just implicit weekly heuristics
- slide titles should remain the source for `Contents` generation so the table of contents reflects the real deck
- text slots may be singular or multiple, and may need horizontal, vertical, or stacked ordering
- image slots should follow the same slot-first philosophy as text slots, including deterministic ordering and fit policy
- generalized template-driven paths should be added in a way that preserves today's working editorial/manual flows until migration is intentional

## Current Constraints

- Supported built-in template names are currently `autoreport_editorial` and `autoreport_manual`, with `weekly_report` retained as a legacy internal alias.
- Default output path is `output/<source-stem>.pptx` when the caller does not provide one.
- The default writer path uses a fresh `Presentation()` if no template path is supplied.
- `autoreport_editorial` is the current editorial built-in profile, and `autoreport_manual` is the current screenshot-first manual built-in profile.
- The legacy `weekly_report` template name is an internal compatibility path layered under the editorial profile rather than the primary public product name.
- Existing slides from a template are cleared before report slides are added.
- The current fit policy prefers the default font size, shrinks as needed, then spills onto continuation slides.
- Diagnostics currently cover font shrink, overflow spill, out-of-bounds risk, and user-template font substitution risk.

## Design Hygiene

- If a task changes the template contract, slot model, contents policy, or template-selection flow, update the matching architecture doc in `docs/architecture/`.
- If a task changes ownership or parallel implementation boundaries for versioned workstreams, update `template-workstreams.md`.
- Prefer documenting new shared interfaces in tests or docs before asking adjacent threads to depend on them.

## Output Contract

- State the pipeline stage being changed: template profiling, content block shaping, fill planning, diagnostics, compatibility, or file writing.
- Cite generation/writer tests for slide structure and template assumptions.
