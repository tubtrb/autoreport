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
- Read `../../../examples/autoreport_editorial_report_content.yaml`.
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

- `report_content` is the primary AI-facing draft contract.
- The primary public authoring contract is `authoring_payload`; `report_payload` remains the compiled runtime payload and backward-compatible input.
- The built-in editorial template contract plus the authoring/runtime example files are part of the public surface.
- Metric items, text-image refs, layout-request matching, and slot override validation are all contract-sensitive and should be updated deliberately.
- The safest AI response shape is one fenced `yaml` code block containing one complete `report_content` document.
- Plain YAML is still accepted for compatibility, but mixed partial YAML where one section is plain text and another is fenced should be treated as invalid broken AI output.
- Representative AI-output regressions belong in loader/web tests so prompt-quality assumptions stay executable.

## Current Design Frame

Treat this section as living schema guidance for the `v0.3` direction.
If the generalized template-driven contract changes, update this skill and the
paired architecture docs together when practical.

The intended template-driven schema flow is:

1. template inspection produces a machine-readable contract
2. `autoreport` exposes that contract plus an AI-facing `report_content` example
3. another AI returns one complete `report_content` YAML document
4. `autoreport` normalizes that into `authoring_payload`
5. `autoreport` compiles it into a `report_payload`
6. validation checks the runtime payload before generation begins

Current design expectations:

- `report_content` is the live AI-facing draft source of truth for external prompting behavior
- `authoring_payload` is the live normalized authoring contract, and `report_payload` is the compiled runtime contract
- legacy weekly-only wording should be treated as compatibility debt, not the primary product frame
- payload fields should stay easy for another AI to fill without reverse-engineering internal slot heuristics
- prompt-facing constraints such as fenced-code-block output shape should be documented in examples/skills and backed by tests, not left as tribal knowledge
- contract and payload validation errors should identify missing, extra, or malformed fields in a deterministic order
- when template-driven payload contracts change, examples and validator-facing tests should change in the same task

## Output Contract

- State which schema rule or normalization path changed.
- Cite loader/schema tests when describing observable behavior.
