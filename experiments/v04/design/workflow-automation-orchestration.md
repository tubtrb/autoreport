# v0.4 Workflow Automation Orchestration

## Problem

The current branch can already inspect a template, emit a starter payload, and
generate a PPTX. What it does not have yet is a branch-local orchestration
surface that describes how those capabilities can be chained into a larger
automation flow without prematurely wiring that flow into `autoreport/`
runtime entrypoints.

## Goals

- define a stable prototype contract for workflow automation in the incubator lane
- make the stages explicit: inspect, draft, validate, generate, review, handoff
- leave space for optional AI-assisted text shaping without forcing it into the
  deterministic runtime path
- keep review and publish gates visible so automation does not skip artifact checks

## Non-goals

- changing the current CLI or web runtime
- claiming that v0.4 automation is product-ready
- replacing deterministic generation with open-ended agent behavior
- deciding the final publish destination or storage policy

## Proposed flow

1. Inspect the template and export `template_contract` plus a scaffolded payload.
2. Draft a `report_payload` from source notes or structured report input.
3. Optionally shape text for audience and tone while preserving contract shape.
4. Validate the payload against `template_id` and generation compatibility rules.
5. Generate a reviewable PPTX artifact.
6. Run a human review gate before any external distribution.
7. Optionally build a publish or handoff packet after review approval.

## Prototype interface

The first branch-local interface lives in
`experiments/v04/prototypes/workflow_automation_spike.py`.

It currently models:

- `AutomationTrigger` for what starts the flow
- `AutomationAsset` for explicit inputs and outputs
- `AutomationStep` for ordered orchestration stages and approval gates
- `AutomationPlan` for the full contract
- `build_template_report_automation_plan(...)` for the default plan builder

## Orchestration reporting adapter

The content automation plan is intentionally separate from branch/worktree
operations, but sandbox runs now emit orchestration-compatible local state under
`.codex/` so the work can be reviewed with the same report-channel policy used
by `v0.3-master`.

The adapter contract is:

- `.codex/workstream.json`
  - local metadata for the incubator worktree
- `.codex/worker-status.json`
  - latest checkpoint status after each sandbox run
- `.codex/worker-final.json`
  - explicit handoff record written only after a separate finalize step

This adapter is evidence-only. It does not turn the incubator branch into a
discovered `v0.3` workstream automatically.

## Upstream policy trace

As of `2026-03-29`, the upstream `codex/v0.3-master` policy head is `0525dc5`.
The main repo now treats these rules as active:

- active task worktrees are discovered from `git worktree list`
- policy changes complete only after `master -> push -> sync_policy_worktrees`
- retired `autoreport_v0.3-*` sibling directories are cleaned through the
  tracked cleanup script, with Codex restart as the first retry step for locked
  empty directories
- `.codex/master-next.txt` is the authoritative branch-specific instruction
  channel, and user-facing chat should fall back to one shared broadcast after
  instruction dispatch

`incubator2` adopts only the reporting-compatible subset of that policy:

- keep `.codex/workstream.json`, `.codex/worker-status.json`, and explicit
  `.codex/worker-final.json` aligned with the collector schema
- keep `.codex/master-next.txt` outside the workflow automation product flow
- do not pull discovery, rebase, push, or cleanup behavior into the automation
  step graph
- do not claim automatic inclusion in the current `codex/v0.3-*` scanner

## Explicit non-goals

The adapter does not import the main repo's git control model into the content
automation flow.

Specifically, it does not:

- generalize `codex/v0.3-*` branch discovery
- run policy sync, rebase, or push steps
- clean retired sibling directories
- treat `.codex/master-next.txt` as part of the product automation contract
- replace the master-thread shared-broadcast policy with sandbox-local chat logic

## Promotion questions

Before any of this moves into `autoreport/` proper, we should be able to answer:

- Which step boundaries belong in runtime code versus external orchestration?
- Which artifacts need stable file or API contracts?
- What evidence is required at the review gate?
- Which evidence belongs in sandbox-local files versus `.codex/` report-channel files?
- Which options stay optional, such as AI text shaping or publish handoff?
- How will failures be mapped back to the existing CLI and web contracts?
