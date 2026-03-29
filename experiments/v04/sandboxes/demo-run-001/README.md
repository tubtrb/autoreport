# demo-run-001

This sandbox rehearses a simple Autoreport-introduction workflow automation
run against the current contract-first engine.

Tracked inputs live under `inputs/`. Generated outputs are recreated by the
sandbox runner and are intentionally ignored under `plans/`, `contracts/`,
`drafts/`, `artifacts/`, `reviews/`, and `logs/`.

The sandbox run also updates local orchestration adapter files under the repo
root `.codex/` directory:

- `.codex/workstream.json`
- `.codex/worker-status.json`

`worker-final.json` is intentionally not written by the normal sandbox run. Use
the explicit finalize helper only after the reviewable artifact is approved.

`.codex/master-next.txt` is also intentionally out of scope here. That file is
reserved for upstream master-thread instruction dispatch, not for branch-local
workflow automation evidence.

Run from the repository root:

```bash
.\.venv\Scripts\python.exe -m experiments.v04.prototypes.workflow_automation_sandbox --sandbox experiments/v04/sandboxes/demo-run-001
```

Finalize an approved run for master-review handoff:

```bash
.\.venv\Scripts\python.exe -m experiments.v04.prototypes.workflow_automation_reporting --sandbox experiments/v04/sandboxes/demo-run-001 --completion-summary "Workflow automation sandbox is ready for review." --known-gaps "Approval is recorded only in local review notes."
```
