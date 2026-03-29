# v0.4 Incubator 2

This directory is the branch-local incubator lane for
`codex/v0.4-incubator2`.

It is intentionally based on `codex/v0.3-master`, not on the older
`codex/v0.4-incubator` branch history. Treat the older worktree as the archive
for weekly-oriented experiments and this directory as the clean `v0.4` reset.

## Current posture

- source of truth: current `v0.3` code, tests, and architecture docs
- product baseline: `autoreport_editorial` plus contract-first generation
- active public shapes: `template_contract`, `report_payload`, and slide kinds
  `text`, `metrics`, `text_image`
- policy: `Lean Reset`
- latest upstream policy trace: `codex/v0.3-master` at `0525dc5`
- Node/PptxGenJS posture: `internal template authoring only`

## Lean Reset rules

- bring over only experiments that still fit the current editorial product
  direction
- retarget weekly-oriented prototypes before treating them as active
- do not copy old weekly sandboxes or preview decks into active `incubator2`
- rebuild validation evidence from fresh runs in this worktree
- keep runtime patches out of scope until the branch-local evidence is clean

## Upstream policy trace

`incubator2` keeps tracking the active `v0.3-master` orchestration policy, but
only the parts that matter to branch-local evidence.

Current retained assumptions:

- `.codex/worker-status.json` and `.codex/worker-final.json` should stay
  collector-compatible
- `.codex/master-next.txt` remains a separate master-thread instruction channel
- `git worktree` discovery, policy sync, and retired-directory cleanup stay in
  the main repo's orchestration layer, not inside the `v0.4` content automation
  plan

See `validation/v0.3-master-policy-trace-2026-03-29.md` for the latest traced
decision log.

## Node authoring posture

`PptxGenJS` stays useful in `incubator2`, but only in a narrow role:

- create internal first-party template fixtures quickly
- iterate on Autoreport-owned editorial looks and placeholder geometry
- hand the generated `.pptx` back to the Python runtime for inspection,
  contract export, and deterministic generation

It is not the product runtime and it is not the product's main value
proposition.

The product still centers on:

- analyzing templates that already exist
- profiling their placeholders safely
- exporting the contract another AI or human can fill
- generating deterministic editable output

See `design/pptxgenjs-authoring-only-decision.md` for the scoped decision.

## Roadmap pointer

The current `v0.4` execution order is documented in
`design/v0.4-roadmap.md`.

That roadmap is intentionally opinionated about where to start:

1. workflow automation
2. mixed-layout hardening
3. first-party template lane
4. external template QA later
5. AI-assisted authoring and delivery flow only after the earlier lanes prove value

## Structure

- `migration-ledger.md`: the carry or retarget decision log
- `design/`: branch-local framing docs tied to the current template-contract
  engine
- `prototypes/`: runnable experiments that stay outside the runtime path
- `validation/`: fresh reports, machine-readable evidence, and promotion checks
- `sandboxes/`: recreated editorial-only rehearsals
