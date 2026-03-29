# v0.4 Branch Boundaries

This note keeps `codex/v0.4-incubator2` operationally separate from the
current `v0.3` delivery flow while staying aligned to the current editorial
contract-first engine.

## What belongs here

- branch-local architecture drafts
- prototype interfaces
- experiment logs and validation checklists
- code spikes that may be rewritten or discarded

## What does not belong here yet

- product claims in the public `README.md`
- changes to CLI or web entrypoints
- changes that make v0.4 part of the current workstream-orchestrator policy
- remote release or publish workflows

## Control-plane boundary

`codex/v0.4-incubator2` is intentionally outside the current `v0.3`
control plane.

That means this branch does not currently participate in:

- `.codex/master-next.txt`
- v0.3 merge-order blockers
- v0.3 overlap hotspot rules

Branch-local exceptions:

- `incubator2` may emit collector-compatible `.codex/worker-status.json` and
  `.codex/worker-final.json` as local evidence adapters
- those files do not make this branch part of the automatic `codex/v0.3-*`
  discovery and sync flow

The older `codex/v0.4-incubator` worktree remains the archive for weekly-first
experiments and is not part of this active lane.

## Promotion trigger

Move work out of `experiments/v04/` only when all of the following are true:

- the interface is stable enough to name publicly
- the runtime boundary is clear
- the tests describe the promoted contract
- the change can be explained without incubator-only context
