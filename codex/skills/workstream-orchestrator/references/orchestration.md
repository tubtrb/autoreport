# Workstream Orchestration Reference

## Workstream keys

- `template-contract-export` -> `autoreport_v0.3-template-contract-export`
- `generic-payload-schema` -> `autoreport_v0.3-generic-payload-schema`
- `text-layout-engine` -> `autoreport_v0.3-text-layout-engine`
- `image-layout-engine` -> `autoreport_v0.3-image-layout-engine`
- `cli-web-template-flow` -> `autoreport_v0.3-cli-web-template-flow`

These worktrees live beside the main repo under the same workspace root.

## Narrow test commands

- `template-contract-export`
  `python -m unittest tests.test_generator tests.test_pptx_writer`
- `generic-payload-schema`
  `python -m unittest tests.test_validator tests.test_loader`
- `text-layout-engine`
  `python -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer`
- `image-layout-engine`
  `python -m unittest tests.test_generator tests.test_pptx_writer`
- `cli-web-template-flow`
  `python -m unittest tests.test_cli tests.test_web_app`

Use the shared repo virtualenv at `.\venv\Scripts\python.exe` from the repo
root unless the user explicitly sets another interpreter.
If you are running from a sibling worktree that does not have its own `.\venv`,
use the main repo interpreter through a relative path such as
`..\autoreport\venv\Scripts\python.exe` or another confirmed shared path.

## Merge order

1. `template-contract-export`
2. `generic-payload-schema`
3. `text-layout-engine`
4. `image-layout-engine`
5. `cli-web-template-flow`

`text-layout-engine` and `image-layout-engine` can move in parallel only after
the contract-export and payload-schema surfaces are stable enough.

## Git ownership policy

- Workers own code changes, local tests, and local WIP commits.
- The master thread owns remote push, rebase, merge, and force-push whenever
  the goal is to preserve a clean shared integration history.
- For tracked shared policy changes under files such as `AGENTS.md`,
  `codex/skills/`, or shared architecture docs, the master thread should land
  the change on the shared base first and then propagate it to sibling
  worktrees by rebase.

## Policy sync mode

Use this mode when the master thread changes tracked shared operating rules.

1. Commit and push the policy change on the shared base.
2. Inspect each sibling worktree for local changes.
3. Create a checkpoint commit if the worktree is dirty.
4. Rebase the branch onto `origin/codex/v0.3-template-engine`.
5. Run the branch's narrow verification command.
6. Push the rebased branch.

Do not rely on `.codex/master-next.txt` as the only channel for a new policy
until the affected branches have actually received that policy through git
history.

## Overlap hotspots

- `autoreport/templates/weekly_report.py`
- `autoreport/templates/autofill.py`
- `autoreport/engine/generator.py`
- `tests/test_generator.py`
- `tests/test_pptx_writer.py`

Raise these files explicitly when you see multiple threads changing them at the
same time.

## Instruction file policy

- Write per-thread next steps into `.codex/master-next.txt`.
- Keep these files local/private and out of tracked product docs.
- Overwrite the file with the newest instruction unless the user asks for an
  append-only log.
- Tell workers to keep `.codex/worker-status.json` current and to create
  `.codex/worker-final.json` only when the branch is ready for master review.

## Report channel policy

Use JSON as the source of truth for worker reports so the master thread can
collect and validate progress programmatically.

### `.codex/worker-status.json`

Use this file for the latest checkpoint status. Overwrite it at each checkpoint.

Required fields:

- `workstream_key`
- `branch`
- `head`
- `updated_at`
- `status`
  Allowed values: `in_progress`, `blocked`, `ready_for_review`
- `task_summary`
- `last_green_test_command`
- `working_tree_clean`
- `evidence.input`
- `evidence.command`
- `evidence.artifact_paths`
  Absolute filesystem paths only
- `evidence.visible_result`
- `evidence.remaining_gap`
- `sync_notes`

Suggested shape:

```json
{
  "workstream_key": "text-layout-engine",
  "branch": "codex/v0.3-text-layout-engine",
  "head": "03e3ed24ac8216acfbf474ada971e84cbc5f5995",
  "updated_at": "2026-03-28T14:32:00+09:00",
  "status": "in_progress",
  "task_summary": "Two-column text slot distribution now follows contract order.",
  "last_green_test_command": ".\\venv\\Scripts\\python.exe -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer",
  "working_tree_clean": false,
  "evidence": {
    "input": "tests/_tmp/two_column_payload.yaml + fixtures/template-two-column.pptx",
    "command": ".\\venv\\Scripts\\python.exe -m autoreport.cli generate --template fixtures/template-two-column.pptx --input tests/_tmp/two_column_payload.yaml --output tests/_tmp/two-column-output.pptx",
    "artifact_paths": [
      "C:\\worktrees\\autoreport_v0.3-text-layout-engine\\tests\\_tmp\\two-column-output.pptx"
    ],
    "visible_result": "The two body items land left-to-right and the Contents slide matches slide titles.",
    "remaining_gap": "Need to lock the vertical stack overflow case."
  },
  "sync_notes": "Do not rebase until template-contract-export freezes the slot naming."
}
```

### `.codex/worker-final.json`

Use this file only when the workstream is ready for master review.

Required fields:

- `workstream_key`
- `branch`
- `head`
- `completed_at`
- `completion_summary`
- `last_green_test_command`
- `primary_artifact_path`
  Absolute filesystem path only
- `artifact_paths`
  Absolute filesystem paths only
- `visible_result`
- `known_gaps`
- `ready_for_master_review`
  Must be `true`

Suggested shape:

```json
{
  "workstream_key": "image-layout-engine",
  "branch": "codex/v0.3-image-layout-engine",
  "head": "2ed749941021458ffceeebce140fa6279dfbb6e3",
  "completed_at": "2026-03-28T16:05:00+09:00",
  "completion_summary": "Contain and cover image placement are now deterministic across portrait and landscape fixtures.",
  "last_green_test_command": ".\\venv\\Scripts\\python.exe -m unittest tests.test_generator tests.test_pptx_writer",
  "primary_artifact_path": "C:\\worktrees\\autoreport_v0.3-image-layout-engine\\tests\\_tmp\\image-layout-output.pptx",
  "artifact_paths": [
    "C:\\worktrees\\autoreport_v0.3-image-layout-engine\\tests\\_tmp\\image-layout-output.pptx",
    "C:\\worktrees\\autoreport_v0.3-image-layout-engine\\tests\\_tmp\\cover-vs-contain.png"
  ],
  "visible_result": "Portrait and landscape images both land in the intended slots and captions follow the matching image.",
  "known_gaps": "No remaining functional gaps for the scoped workstream.",
  "ready_for_master_review": true
}
```

## Collector policy

- Run `collect_worker_reports.py` after `worktree_snapshot.py` when you need the
  latest orchestration picture.
- The collector should validate JSON parsing, required fields, absolute paths,
  and artifact existence.
- The collector summary should make these booleans easy to scan per workstream:
  `report_missing`, `status_stale`, `ready_for_review`, `final_present`.
- Final review still requires opening `primary_artifact_path` for visual
  verification.

## Functional evidence policy

When the user cares about whether the product behavior really works, do not ask
workers to report only code status.

Require each checkpoint report to include:

1. the input used for the check, such as template path, YAML, JSON, or image
2. the execution command
3. the output artifact path
4. the visible or behavioral result
5. the remaining gap

Require each completion report to include at least one absolute filesystem path
that the user can open directly for visual verification. Prefer the generated
`.pptx` itself when available. Supporting screenshots or exported contract files
are helpful, but they do not replace the final artifact path.

Keep non-committed proof artifacts under `tests/_tmp/` or another clearly local
path. Do not promote proof artifacts into tracked docs or product paths unless
the user explicitly asks for that.
