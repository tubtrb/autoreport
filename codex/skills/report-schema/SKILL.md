---
name: report-schema
description: Handle YAML loading, report models, contract/payload validation, example payloads, and schema-facing tests for the current Autoreport format.
---

# Report Schema

## Overview

Use this skill for `autoreport/loader.py`, `autoreport/models.py`,
`autoreport/validator.py`, the public example contract/payload files, and the loader/schema tests.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/weekly-report-schema.md`.
- If the task affects generalized template-driven payloads, also read:
  - `../../../docs/architecture/template-aware-autofill-engine.md`
  - `../../../docs/architecture/v0.3-template-workstreams.md`
- Read `../../../autoreport/loader.py`, `../../../autoreport/models.py`, and `../../../autoreport/validator.py`.
- Read `../../../examples/autoreport_editorial_template_contract.yaml`.
- Read `../../../examples/autoreport_editorial_authoring_payload.yaml`.
- Read `../../../examples/autoreport_editorial_report_payload.yaml`.
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
- Keep the contract and payload models aligned with validator expectations.
- Update the public example contract/payload files whenever required fields or slot rules change.
- Update tests in the same change when error wording or allowed keys change.

4. Treat legacy wording intentionally.
- The validator currently rejects `report_type` with error text that mentions `v0.1`.
- Preserve that string unless the task intentionally updates the tested contract everywhere it appears.

## Current Constraints

- The primary public authoring contract is `authoring_payload`; `report_payload` remains the compiled runtime payload and backward-compatible input.
- The built-in editorial template contract plus the authoring/runtime example files are part of the public surface.
- Metric items, text-image refs, layout-request matching, and slot override validation are all contract-sensitive and should be updated deliberately.

## Current Design Frame

Treat this section as living schema guidance for the `v0.3` direction.
If the generalized template-driven contract changes, update this skill and the
paired architecture docs together when practical.

The intended template-driven schema flow is:

1. template inspection produces a machine-readable contract
2. `autoreport` exposes that contract as YAML or JSON skeletons
3. a human or another AI fills an `authoring_payload`
4. `autoreport` compiles it into a `report_payload`
5. validation checks the runtime payload before generation begins

Current design expectations:

- `authoring_payload` is the live public source of truth for shipped authoring behavior, and `report_payload` is the compiled runtime contract
- legacy weekly-only wording should be treated as compatibility debt, not the primary product frame
- payload fields should stay easy for another AI to fill without reverse-engineering internal slot heuristics
- contract and payload validation errors should identify missing, extra, or malformed fields in a deterministic order
- when template-driven payload contracts change, examples and validator-facing tests should change in the same task

## Output Contract

- State which schema rule or normalization path changed.
- Cite loader/schema tests when describing observable behavior.
