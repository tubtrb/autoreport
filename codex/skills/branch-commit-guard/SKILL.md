---
name: branch-commit-guard
description: Guard direct commits on protected integration branches in `autoreport`. Use before staging, committing, or pushing when the current branch may be `codex/next` or `codex/master`, or when choosing a safe child branch for work.
---

# Branch Commit Guard

## Overview

Use this skill before staging, committing, or pushing in `autoreport` when the
checked-out branch may be a protected integration branch.
It blocks routine Codex-authored direct commits on `codex/next` and
`codex/master`, while leaving `codex/v<next>-master` available for direct work
under the current repo policy. It does not block intentional protected-branch
integration work such as release promotion, merge or squash promotion, branch
sync, or post-release cleanup.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- If the task is about release promotion, merge cleanup, or branch sync, also
  read `../release-tagging/SKILL.md`.
- Read `scripts/ensure_safe_branch.py` only when you need to patch or inspect
  the guard implementation itself.

## Current Branch Rules

- Protected exact branch names: `codex/next`, `codex/master`
- Allowed for direct commits by default: `main`, `codex/v<next>-master`, and
  ordinary task branches such as `codex/v0.4-web-copy`
- `codex/v<next>-master` is intentionally not blocked by this skill because the
  current repo policy allows direct commits there.
- Bypass the protected-branch block when the work is intentional integration
  history on `codex/next` or `codex/master`, such as release promotion, merge
  or squash promotion, branch sync, or post-release cleanup.
- Also bypass it when the user explicitly authorizes another direct commit on
  `codex/next` or `codex/master`.

## Workflow

1. Check the branch before staging or committing.
- Run `.\venv\Scripts\python.exe codex/skills/branch-commit-guard/scripts/ensure_safe_branch.py`
  from the repo root.
- Use `--branch <name>` when planning or testing without relying on the current
  checkout.

2. Stop routine development on protected branches by default.
- If the script reports `codex/next` or `codex/master`, do not stage or commit
  there for routine feature work.
- Create or switch to a child branch first, for example
  `codex/next-<task>` or `codex/master-<task>`.
- Keep the protected branch for curated merges, syncs, or explicit user
  overrides rather than routine incremental commits.

3. Continue normally on allowed branches.
- A passing result means the current branch is allowed for direct commits under
  the current repo policy.
- `codex/v<next>-master` remains a valid direct-commit line unless the user
  asks for a narrower task-branch workflow for that specific effort.

4. Use overrides sparingly.
- Pass `--allow-protected` when you are intentionally updating protected-branch
  integration history, for example during release promotion, merge or squash
  promotion, branch sync, or release cleanup.
- Pass `--allow-protected` when the user explicitly asks for another direct
  commit on `codex/next` or `codex/master`.
- When using the override, say so in chat before staging or committing.

## Script Contract

- Exit `0`: branch is allowed, or the user-approved override was supplied
- Exit `2`: branch is protected and direct commit should stop
- The script prints a suggested child branch name, which can be customized with
  `--task <slug>`

## Output Contract

- State the checked branch.
- State whether it is protected by this skill.
- State whether you stayed on the branch for protected-branch integration work,
  stayed with another explicit user-approved override, or moved to a child
  branch first.
