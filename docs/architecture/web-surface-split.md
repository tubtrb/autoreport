# Web Surface Split

This note explains why Autoreport now keeps the user-facing web app and the
developer-facing debug app separate.

## Why the split exists

The product flow and the debugging flow serve different users.

The product flow is:

1. start from one built-in starter example
2. edit the YAML directly
3. keep the public-web draft to text or metrics slides
4. generate the deck

The debugging flow is:

1. inspect the full template contract
2. inspect normalization from `report_content` to `authoring_payload`
3. inspect compilation into `report_payload`
4. inspect upload refs and error states for image-backed drafts
5. verify the shared routes and generation path end to end

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
- text-first helper copy about supported public slide kinds
- a clear handoff to the debug app or CLI when images are needed

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

- one shared generation pipeline
- one base error shape
- one generation path
- no duplicated schema logic

The split is mostly a UI split. The public app also adds one product guardrail:
it rejects image-backed drafts so the default hosted surface stays text-first.

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
