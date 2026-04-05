# Web Surface Split

This note explains why Autoreport now keeps the user-facing web app and the
developer-facing debug app separate.

## Why the split exists

The product flow and the debugging flow serve different users.

The product flow is:

1. start from the built-in manual procedure starter
2. edit the YAML directly
3. keep the public-web draft on the manual screenshot workflow
4. generate the deck

The debugging flow is:

1. inspect the full template contract
2. inspect normalization from `report_content` to `authoring_payload`
3. inspect compilation into `report_payload`
4. inspect upload refs and error states for image-backed drafts
5. verify the shared routes and generation path end to end
6. inspect failures or representative samples from broader robustness runs without pushing that bulk workflow into the public app

Trying to serve both flows in one screen made the product surface too noisy and
encouraged manual slide-building controls that are not the intended user path.

## Surface responsibilities

### User app

File:

- `autoreport/web/app.py`

Intent:

- optimize for one clean user flow
- default to one editable starter example
- keep slide count dynamic and derived from the draft itself
- keep contract inspection and compiled runtime inspection out of the default user surface

Allowed UI:

- one large input area
- one or two primary actions
- one built-in manual starter summary
- paired screenshot upload and customer-facing slide preview rows for the manual starter
- a clear handoff to the debug app or CLI when deeper inspection or custom template/image control is needed

Avoid in the user app:

- multi-pane debug dashboards
- manual slide-builder controls
- many helper buttons for constructing individual slides
- developer-only inspection clutter

### Debug app

File:

- `autoreport/web/debug_app.py`

Intent:

- give developers a place to inspect every stage of the web contract
- verify normalization and compiled payloads without polluting the user app
- preserve one shared generation pipeline under the hood
- act as the inspection surface for robustness-validation work, while keeping the actual high-volume execution outside the browser UI

Allowed UI:

- multiple panes
- starter payload loaders
- normalization/compile helpers
- explicit contract and runtime views
- extra upload inspection controls
- summary views for corpus or template validation runs
- targeted rerun controls for selected failing or representative cases

Keep out of the debug app when the work is high-volume by nature:

- long-running bulk compile/generate loops across large prompt corpora
- orchestration that should be resumable from the command line or CI
- test-runner responsibilities that are better expressed as files, JSON summaries, or CLI reports

## Shared API contract

Both apps should continue to share the same core API behavior:

- `POST /api/compile`
- `POST /api/generate`
- `GET /healthz`

That means:

- one shared generation pipeline
- one base error shape
- one generation path
- no duplicated schema logic

The split is mostly a UI split. The public app also adds template-specific
guardrails:

- the public homepage now leads directly with the built-in manual starter
- the built-in manual starter allows ordered image-backed drafts on the manual template
- deeper inspection panes still stay in the debug app

## Input contract posture

The apps accept three surfaces:

- `report_content`
- `authoring_payload`
- legacy `report_payload`

`report_content` is the AI-facing draft contract.
`authoring_payload` is the normalized authoring contract.
`report_payload` is the compiled runtime contract.

The user app should lead with `report_content`.
The debug app may inspect all three more explicitly.

## Validation Workbench Policy

When future work needs confidence across hundreds or thousands of draft variations,
split the job into two layers:

1. a CLI or batch runner executes the large compile/generate matrix and writes structured summaries
2. the debug app reads those summaries so a developer can inspect failures, compare normalized and compiled payloads, and rerun a small selected case

This keeps the public product surface simple, keeps long-running robustness work scriptable, and still gives the web layer a useful place to analyze failures.

## Operational rule

When future work needs more inspection, debugging, or manual controls:

- first ask whether the feature belongs in the debug app
- if the feature is really bulk robustness execution, keep the execution in a runner and expose only inspection or selected-case rerun controls in the debug app
- only add it to the user app if it improves the primary user flow directly

This rule exists to prevent debug clutter from re-entering the product surface.
