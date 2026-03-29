# PptxGenJS Authoring-Only Decision

## Decision

Adopt `PptxGenJS` in `codex/v0.4-incubator2` only as an internal template
authoring tool.

Do not adopt it as the product runtime.

## Why this is the right boundary

Autoreport's main product value is not template creation.
The main value is:

- receiving an already-existing template
- profiling its placeholders and layout structure
- exporting a fillable contract
- validating a payload against that contract
- generating a deterministic editable `.pptx`

That runtime responsibility already lives in Python and matches the current
public product framing.

## What `PptxGenJS` is good for here

- quickly creating first-party seed templates while external template sources
  do not yet exist
- experimenting with Autoreport-owned editorial looks
- producing branch-local fixtures for placeholder and layout diagnostics
- iterating on text-first placeholder geometry faster than hand-authoring every
  test template

## What stays in Python

- template inspection
- `template_contract` export
- `report_payload` scaffolding and validation
- deterministic fill planning
- `python-pptx` writing path
- runtime diagnostics and compatibility policy

## Non-goals

- moving the product runtime to Node.js
- reimplementing contract export in Node.js
- making template creation the primary user-facing product story
- adding Node.js to CLI or web runtime deployment requirements

## Current evidence

- text-first authored templates are useful and reproducible
- mixed image/text authoring is not yet strong enough to justify a runtime
  shift
- the current runtime architecture explicitly keeps external authoring tools out
  of the runtime path

## Operational rule for `incubator2`

When a `PptxGenJS` change is proposed in `experiments/v04/`, evaluate it with
this question first:

`Does this help us create or refine first-party templates without changing the Python runtime contract?`

If the answer is yes, it fits the lane.
If the answer is no, it should be treated as a separate architecture decision.
