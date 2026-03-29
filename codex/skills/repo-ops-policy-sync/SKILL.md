---
name: repo-ops-policy-sync
description: Operate Autoreport's shared repo control surface. Use when Codex changes `AGENTS.md`, repo-local skills under `codex/skills/`, tracked deployment handover docs, or other shared architecture or process guidance that future Codex turns rely on, and the task must finish operationally with validation, public-repo-safety, a commit on `main`, a push to `origin/main`, and a `codex/next` refresh from that pushed `main`.
---

# Repo Ops Policy Sync

## Overview

Use this skill for shared repo-operation work rather than product-feature work.
It covers the corner case where the task looks like "just docs" but the edited
files are actually part of the live operating surface for future agents, so the
job is not complete until the shared branch state has been updated on origin.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `references/finish-checklist.md`.
- Read `../public-repo-safety/SKILL.md`.
- If the task touches tracked deployment handover or EC2 guidance, also read
  `../remote-deployment-handover/SKILL.md`.
- If the task touches product-facing README or release wording instead of repo
  operations, switch to `../release-docs/SKILL.md` as the primary skill.
- If the task also needs release tags or nontrivial branch normalization, also
  read `../release-tagging/SKILL.md`.
- If the task is really the master-thread workstream flow on
  `codex/v0.3-master`, switch to `../workstream-orchestrator/SKILL.md` instead
  of forcing the ordinary `main` plus `codex/next` path.

## Workflow

1. Recognize repo-operation surfaces early.
- Treat `AGENTS.md`, `codex/skills/`, tracked deployment handover notes, and
  shared architecture or process docs as repo-operation files when they change
  how later Codex turns should behave.
- Do not downgrade those files into "docs-only polish" when they are actually
  changing the repository's operating rules.

2. Treat completion as operational, not advisory.
- Unless the user explicitly asks to stop earlier or use another branch, do not
  stop after editing the files.
- The default finish bar for this skill is: validate the changed operating
  surface, run `public-repo-safety`, commit on `main`, push `origin/main`,
  refresh `codex/next` from that pushed `main`, and return the workspace to
  `main`.

3. Validate narrowly but concretely.
- Run `quick_validate.py` for any new or edited repo-local skill folder.
- If the changed guidance makes claims about a tested runtime behavior, run the
  narrow matching tests before pushing.
- If the change is guidance-only and grounded in already-inspected code or
  tests, cite that source of truth instead of inventing extra verification.

4. Keep the push scope clean.
- Stage only the intended repo-operation files.
- If unrelated tracked changes are present, do not silently bundle them into the
  policy commit.
- If `main` is not the working branch for a normal repo-operation task, move the
  change onto `main` or stop and realign before calling the task complete.

5. Run the shared-branch sync loop.
- Push `main` before touching `codex/next`.
- Refresh `codex/next` from the pushed `main` with a fast-forward when
  possible.
- If `codex/next` cannot fast-forward cleanly, stop and resolve the branch state
  explicitly instead of guessing.

6. Report the operational result.
- Record the commit SHA that landed on `main`.
- Record whether `codex/next` now points to the same commit.
- Call out any blocker that prevented the full finish loop from completing.

## Current Repo Defaults

- Shared repo-operation work normally lands directly on `main`.
- `codex/next` should mirror the pushed `main` commit after this skill finishes.
- `public-repo-safety` is required before public push or publish claims.
- A local-only edit to the shared operating surface is incomplete by default.

## Output Contract

- State that `repo-ops-policy-sync` was used.
- Name the shared operating-surface files that changed.
- State the validation run for those files.
- State whether `public-repo-safety` found blockers.
- State the `main` commit SHA that was pushed.
- State whether `codex/next` was refreshed to the same commit.
