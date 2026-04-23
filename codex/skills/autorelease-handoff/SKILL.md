---
name: autorelease-handoff
description: Sync versioned public posts from `autoreport/docs/posts/` plus stable standalone public pages from `autoreport/docs/pages/` into the private `autorelease` publishing repository, rewrite or copy them into the handoff contract, and validate the touched content.
---

# Autorelease Handoff

## Overview

Use this skill when `autoreport` has versioned public posts under `docs/posts/`
or stable standalone public pages under `docs/pages/` and they should be
delivered into the private `autorelease` repository.

This skill is especially important when:

- a branch is being wrapped up
- a tag is about to be created
- versioned development logs, guides, or release notes are ready
- standalone public pages need to be synced or refreshed
- the user explicitly asks to sync content into `autorelease`

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../write-doc-markdown/SKILL.md` when the source post text is still being edited.
- Read `../public-repo-safety/SKILL.md` before final public signoff.
- Read `../../../docs/deployment/public-service-info.yaml`.
- Read the sibling `autorelease` repository files:
  - `../autorelease/docs/authoring-contract.md`
  - `../autorelease/src/autorelease/content.py`
  - `../autorelease/src/autorelease/validate.py`
- Read `references/handoff-contract.md`.

## Workflow

1. Confirm the source files.
- Versioned source paths live under `docs/posts/`.
- Stable standalone public page sources live under `docs/pages/`.
- Default version comes from `pyproject.toml` unless the user overrides it.

2. Run the automated handoff script.
- Default command:
  - `.\venv\Scripts\python.exe codex/skills/autorelease-handoff/scripts/handoff_posts_to_autorelease.py`
- Common explicit form:
  - `.\venv\Scripts\python.exe codex/skills/autorelease-handoff/scripts/handoff_posts_to_autorelease.py --version <version> --source-ref codex/v<version>-master`

3. Let the script own the contract conversion.
- It rewrites the versioned source posts into the `autorelease` front matter contract.
- It copies publishable standalone page sources from `docs/pages/` into `content/pages/`.
- It copies local screenshot/image assets into `content/assets/<slug>/`.
- It keeps the tracked live-service block aligned from `docs/deployment/public-service-info.yaml`
  so the stable guide page and the `autorelease` homepage can point to the
  current public site and hosted demo.
- It validates only the touched posts and copied standalone pages so unrelated dirty work in `autorelease` does not block the handoff.

4. Report the result clearly.
- State which source version was handed off.
- Name the target files in `autorelease`.
- State whether targeted validation passed.
- If `autorelease` still has unrelated dirty files, call that out instead of pretending the target repo is fully clean.

## Current Defaults

- Source repo: the current `autoreport` workspace
- Target repo: the sibling `autorelease` workspace
- Expected versioned source files:
  - `docs/posts/autoreport-v<version>-development-log.md`
  - `docs/posts/autoreport-guide-v<version>.md`
  - `docs/posts/autoreport-v<version>-release-notes.md`
- Expected stable standalone public page sources:
  - `docs/pages/*.md`
- The versioned Markdown files above are repo-tracked handoff source files, while versioned screenshot capture folders under `docs/posts/*-image-v*/` stay local-only unless explicitly promoted.
- `docs/pages/*.md` is the source of truth for `autoreport`-owned appendix-style standalone pages that publish into `../autorelease/content/pages/`.
- Expected source asset directories:
  - `docs/posts/devlog-image-v<version>/`
  - `docs/posts/guide-image-v<version>/`
- Shared guide insert screenshots live under `docs/shared-assets/user-guide-ai-insert/` and are copied into `content/assets/guide/ai-insert/` during handoff.
- Guide handoff currently updates the stable `guide` page in `autorelease` rather than creating a versioned guide slug there.
- Matching standalone target pages under `../autorelease/content/pages/` should not be direct-edited when the source file already exists under `docs/pages/`; edit the source file and rerun the handoff instead.
- The handoff also keeps `../autorelease/content/pages/main.md` aligned with the
  tracked live-service block.

## Output Contract

- State the version and `source_ref` used for the handoff.
- Cite the exact target file paths written in `autorelease`.
- State whether touched-post validation passed.
- Call out missing source files, missing assets, or contract violations as blockers.
