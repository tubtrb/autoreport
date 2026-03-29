---
name: autorelease-handoff
description: Sync versioned public posts from `autoreport/docs/posts/` into the private `autorelease` publishing repository, rewrite them into the handoff contract, copy local assets, and validate the touched posts.
---

# Autorelease Handoff

## Overview

Use this skill when `autoreport` has versioned public posts under `docs/posts/`
and they should be delivered into the private `autorelease` repository.

This skill is especially important when:

- a branch is being wrapped up
- a tag is about to be created
- versioned development logs, guides, or release notes are ready
- the user explicitly asks to sync content into `autorelease`

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../write-doc-markdown/SKILL.md` when the source post text is still being edited.
- Read `../public-repo-safety/SKILL.md` before final public signoff.
- Read the sibling `autorelease` repository files:
  - `../autorelease/docs/authoring-contract.md`
  - `../autorelease/src/autorelease/content.py`
  - `../autorelease/src/autorelease/validate.py`
- Read `references/handoff-contract.md`.

## Workflow

1. Confirm the versioned source files.
- Default source paths are version-specific files under `docs/posts/`.
- Default version comes from `pyproject.toml` unless the user overrides it.

2. Run the automated handoff script.
- Default command:
  - `.\venv\Scripts\python.exe codex/skills/autorelease-handoff/scripts/handoff_posts_to_autorelease.py`
- Common explicit form:
  - `.\venv\Scripts\python.exe codex/skills/autorelease-handoff/scripts/handoff_posts_to_autorelease.py --version 0.2.1 --source-ref v0.2.1`

3. Let the script own the contract conversion.
- It rewrites the versioned source posts into the `autorelease` front matter contract.
- It copies local screenshot/image assets into `content/assets/<slug>/`.
- It validates only the touched posts so unrelated dirty work in `autorelease` does not block the handoff.

4. Report the result clearly.
- State which source version was handed off.
- Name the target files in `autorelease`.
- State whether targeted validation passed.
- If `autorelease` still has unrelated dirty files, call that out instead of pretending the target repo is fully clean.

## Current Defaults

- Source repo: the current `autoreport` workspace
- Target repo: the sibling `autorelease` workspace
- Expected staged source files:
  - `docs/posts/autoreport-v<version>-development-log.md`
  - `docs/posts/autoreport-guide-v<version>.md`
  - `docs/posts/autoreport-v<version>-release-notes.md`
- Expected source asset directories:
  - `docs/posts/devlog-image-v<version>/`
  - `docs/posts/guide-image-v<version>/`

## Output Contract

- State the version and `source_ref` used for the handoff.
- Cite the exact target file paths written in `autorelease`.
- State whether touched-post validation passed.
- Call out missing source files, missing assets, or contract violations as blockers.
