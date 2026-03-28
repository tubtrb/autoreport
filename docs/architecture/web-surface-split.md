# Web Surface Split

This note explains why Autoreport now keeps the user-facing web app and the
developer-facing debug app separate.

## Why the split exists

The product flow and the debugging flow serve different users.

The product flow is:

1. copy one prompt package
2. ask another AI for a `report_content` draft with however many slides are needed
3. paste the returned YAML
4. optionally upload real image files
5. generate the deck

The debugging flow is:

1. inspect the full template contract
2. inspect normalization from `report_content` to `authoring_payload`
3. inspect compilation into `report_payload`
4. inspect upload refs and error states
5. verify the shared routes and generation path end to end

Trying to serve both flows in one screen made the product surface too noisy and
encouraged manual slide-building controls that are not the intended user path.

## Surface responsibilities

### User app

File:

- `autoreport/web/app.py`

Intent:

- optimize for one clean user flow
- default to an AI-facing `report_content` prompt
- keep slide count dynamic and derived from the draft itself
- keep contract inspection and compiled runtime inspection secondary and optional

Allowed UI:

- one large input area
- one or two primary actions
- optional collapsed views for template contract and compiled runtime payload
- upload controls for real image files

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

Allowed UI:

- multiple panes
- starter payload loaders
- normalization/compile helpers
- explicit contract and runtime views
- extra upload inspection controls

## Shared API contract

Both apps should continue to share the same core API behavior:

- `POST /api/compile`
- `POST /api/generate`
- `GET /healthz`

That means:

- one validation policy
- one error shape
- one generation path
- no duplicated schema logic

The split is a UI split, not a runtime split.

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

## Operational rule

When future work needs more inspection, debugging, or manual controls:

- first ask whether the feature belongs in the debug app
- only add it to the user app if it improves the primary user flow directly

This rule exists to prevent debug clutter from re-entering the product surface.
