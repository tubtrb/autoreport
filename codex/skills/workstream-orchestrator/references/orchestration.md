# Workstream Orchestration Reference

## Discovery model

- Discover active task worktrees from `git worktree list --porcelain`.
- Default branch scope is `codex/v0.3-*`.
- Default exclusions:
  - `codex/v0.3-master`
  - `codex/v0.3-bootstrap-*`
  - `codex/v0.3-salvage-*`
- Any active task worktree may optionally define local orchestration metadata in
  `.codex/workstream.json`.

Suggested local shape:

```json
{
  "key": "web-authoring-ux",
  "test_modules": ["tests.test_web_app"],
  "orchestration_enabled": true
}
```

If local metadata is missing, the scripts should derive the workstream key from
the branch suffix and infer a narrow test recipe from the branch name.

## Current active task branches

- `codex/v0.3-contract-hardening`
- `codex/v0.3-web-authoring-ux`
- `codex/v0.3-generation-preview`
- `codex/v0.3-release-prep`

These branches may or may not all have live sibling worktrees at a given
moment; orchestration scripts should operate on the discovered worktree set, not
the branch list alone.

## Narrow test defaults

The discovery helper may infer narrow verification commands from branch names:

- `contract*`, `schema*`, `payload*`
  - `python -m unittest tests.test_loader tests.test_validator`
- `web*`, `cli*`
  - `python -m unittest tests.test_cli tests.test_web_app`
- `generation*`, `preview*`, `layout*`, `template*`, `image*`, `text*`
  - `python -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer`
- `release*`
  - `python -m unittest tests.test_cli tests.test_web_app`

If a worktree provides `.codex/workstream.json`, its `test_modules` list should
override the inferred default.

Use the shared repo virtualenv at `.\venv\Scripts\python.exe` from the repo
root unless the user explicitly sets another interpreter.

## Merge order

1. `codex/v0.3-contract-hardening`
2. `codex/v0.3-generation-preview`
3. `codex/v0.3-web-authoring-ux`
4. `codex/v0.3-release-prep`

`generation-preview` and `web-authoring-ux` may move in parallel once contract
field names and slot rules are stable enough.

## Git ownership policy

- Workers own code changes, local tests, and local WIP commits.
- The master thread owns remote push, rebase, merge, and force-push whenever
  the goal is to preserve a clean shared integration history.
- For tracked shared policy changes under files such as `AGENTS.md`,
  `codex/skills/`, or shared architecture docs, the master thread should land
  the change on the shared base first and then propagate it to active task
  worktrees by rebase or forward merges.

## Policy sync mode

Use this mode when the master thread changes tracked shared operating rules.

1. Commit and push the policy change on `codex/v0.3-master`.
2. Inspect each active task worktree for local changes.
3. Create a checkpoint commit if the worktree is dirty.
4. Rebase the task branch onto `origin/codex/v0.3-master`.
5. Run the branch's narrow verification command.
6. Push the rebased branch.

Do not rely on `.codex/master-next.txt` as the only channel for a new policy
until the affected branches have actually received that policy through git
history.

## Overlap hotspots

- `autoreport/template_flow.py`
- `autoreport/models.py`
- `autoreport/validator.py`
- `autoreport/templates/weekly_report.py`
- `autoreport/templates/autofill.py`
- `autoreport/engine/generator.py`
- `autoreport/outputs/pptx_writer.py`
- `autoreport/web/app.py`
- `tests/test_generator.py`
- `tests/test_pptx_writer.py`
- `tests/test_web_app.py`

Raise these files explicitly when you see multiple threads changing them at the
same time.

## Instruction file policy

- Write per-thread next steps into `.codex/master-next.txt`.
- Keep these files local/private and out of tracked product docs.
- Overwrite the file with the newest instruction unless the user asks for an
  append-only log.
- Tell workers to keep `.codex/worker-status.json` current and to create
  `.codex/worker-final.json` only when the branch is ready for master review.
- Treat `.codex/master-next.txt` as the source of truth for branch-specific
  work.
- After updating these files, the shared worker-facing broadcast can stay
  generic: reload the latest policy/skill files, then follow local
  `.codex/master-next.txt`.

## Report channel policy

Use JSON as the source of truth for worker reports so the master thread can
collect and validate progress programmatically.

### `.codex/worker-status.json`

Use this file for the latest checkpoint status. Overwrite it at each
checkpoint.

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
`.pptx` itself when available.
