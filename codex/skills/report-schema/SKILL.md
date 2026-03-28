---
name: report-schema
description: Handle YAML loading, report models, schema validation, example payloads, and schema-facing tests for the weekly report format.
---

# Report Schema

## Overview

Use this skill for `autoreport/loader.py`, `autoreport/models.py`,
`autoreport/validator.py`, `examples/weekly_report.yaml`, and the loader/schema tests.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/weekly-report-schema.md`.
- If the task affects generalized template-driven payloads, also read:
  - `../../../docs/architecture/template-aware-autofill-engine.md`
  - `../../../docs/architecture/v0.3-template-workstreams.md`
- Read `../../../autoreport/loader.py`, `../../../autoreport/models.py`, and `../../../autoreport/validator.py`.
- Read `../../../examples/weekly_report.yaml`.
- Read `../../../tests/test_loader.py` and `../../../tests/test_validator.py`.
- If schema changes affect generation or web responses, inspect `../../../tests/test_cli.py` and `../../../tests/test_web_app.py`.

## Workflow

1. Keep parsing and validation separate.
- `loader.py` should only handle file presence, reading, and YAML parsing.
- `validator.py` should own schema rules, normalization, and aggregated error collection.

2. Preserve observable validation order.
- Error ordering is locked in tests.
- Add new rules carefully so existing errors do not reorder by accident.

3. Update schema surfaces together.
- Keep `WeeklyReport` and validator expectations aligned.
- Update `examples/weekly_report.yaml` whenever required fields or metric keys change.
- Update tests in the same change when error wording or allowed keys change.

4. Treat legacy wording intentionally.
- The validator currently rejects `report_type` with error text that mentions `v0.1`.
- Preserve that string unless the task intentionally updates the tested contract everywhere it appears.

## Current Constraints

- The accepted payload is a YAML mapping for a weekly report.
- Required top-level keys are `title`, `team`, `week`, `highlights`, `metrics`, `risks`, and `next_steps`.
- Allowed metrics are `tasks_completed` and `open_issues`.
- Metric values must be integers greater than or equal to `0`, and booleans are rejected.
- Extra top-level fields and extra metric keys are rejected.
- `week` is currently validated only as a non-empty string.

## Current Design Frame

Treat this section as living schema guidance for the `v0.3` direction.
If the generalized template-driven contract changes, update this skill and the
paired architecture docs together when practical.

The intended template-driven schema flow is:

1. template inspection produces a machine-readable contract
2. `autoreport` exposes that contract as YAML or JSON skeletons
3. a human or another AI fills the payload
4. validation checks the payload before generation begins

Current design expectations:

- the current weekly-report schema is still the live source of truth for shipped behavior until a migration path is explicit
- generalized template-driven payloads should be additive first, not a silent replacement of the weekly contract
- payload fields should stay easy for another AI to fill without reverse-engineering internal slot heuristics
- contract and payload validation errors should identify missing, extra, or malformed fields in a deterministic order
- when template-driven payload contracts change, examples and validator-facing tests should change in the same task

## Output Contract

- State which schema rule or normalization path changed.
- Cite loader/schema tests when describing observable behavior.
