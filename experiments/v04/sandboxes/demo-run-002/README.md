# demo-run-002

This sandbox rehearses workflow automation alpha against a mixed user-owned
template instead of the built-in editorial baseline.

The template source is the branch-local PptxGenJS fixture:

- `experiments/v04/prototypes/pptxgenjs_template_spike/generated/v04-text-image-template.pptx`

Tracked inputs stay under `inputs/`. Regenerated outputs remain local under
`plans/`, `contracts/`, `drafts/`, `artifacts/`, `reviews/`, and `logs/`.

Run from the repository root:

```bash
.\.venv\Scripts\python.exe -m experiments.v04.prototypes.workflow_automation_sandbox --sandbox experiments/v04/sandboxes/demo-run-002
```
