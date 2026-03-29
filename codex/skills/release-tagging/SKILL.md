---
name: release-tagging
description: Create release backup tags in the autoreport repository, clean up merged source branches, and refresh `codex/next` from `main` after a release merge. Use when a version should be preserved with an annotated git tag or when the post-merge branch flow needs to be normalized.
---

# Release Tagging

## Overview

Use this skill for repository-local release backup tagging and the matching
post-merge branch cleanup flow.

Default release flow in this repository:

1. merge the release branch into `main`
2. create an annotated `v<version>` tag on the merged `main` commit
3. push the tag
4. delete the merged source branch unless the user wants to keep it
5. refresh `codex/next` from the updated `main`

This skill is repo-local only. It does not manage the sibling `autorelease`
repository unless the user explicitly asks for that separate flow.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../../../pyproject.toml` for the package version.
- Read `../../../README.md` when public version framing matters.
- Read `../public-repo-safety/SKILL.md` before public push or tag signoff.
- If the tag depends on fresh ship confidence, also read `../release-verification/SKILL.md`.

## Workflow

1. Confirm the release target.
- Default the tag name to `v<project.version>` from `pyproject.toml`.
- Prefer tagging the merged `main` release commit, not a deleted source branch tip.
- If the release branch has already been merged, tag the merge commit on `main`.

2. Protect existing tags.
- If the target tag already exists locally and on origin at the expected commit, report that it is already in place.
- If the tag exists at a different commit, stop and ask before moving or recreating it.
- Prefer annotated tags with a short release message such as `Release v0.3.0`.

3. Push the tag intentionally.
- Push the tag explicitly with `git push origin <tag>`.
- Report the exact commit SHA that the tag now points to.

4. Normalize the branch flow after merge.
- Delete the merged source branch locally and on origin when the user asks for cleanup.
- Refresh `codex/next` from the pushed `main` commit.
- If `codex/next` has drifted, recreate it from `main` instead of guessing at a merge.

## Current Defaults

- Release tags use the form `v<semantic-version>`.
- `main` is the post-merge source of truth for backup tags.
- `codex/next` should mirror the updated `main` commit after release cleanup.

## Output Contract

- State the tag name and the commit SHA it points to.
- State whether the tag was newly created or already existed.
- State which source branch, if any, was deleted.
- State whether `codex/next` was refreshed from `main`.
