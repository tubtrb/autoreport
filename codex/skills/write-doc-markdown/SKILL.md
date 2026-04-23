---
name: write-doc-markdown
description: Generate WordPress-style Markdown posts for the autoreport repository, including Korean development logs plus English release notes and user guides. Use when Codex needs to draft or save a public-facing `.md` post that should match the existing auto-report.org writing patterns while staying grounded in the current repo code, tests, README, and package metadata.
---

# Write Doc Markdown

## Overview

Use this skill to write WordPress-ready Markdown posts that fit the existing
Autoreport public voice. It supports three fixed modes:
`개발 일지`, `릴리즈 노트`, and `사용 가이드`.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../../../README.md` and `../../../pyproject.toml`.
- Read `../../../docs/deployment/public-service-info.yaml` when the post may be handed off into `autorelease` or should mention the live public service.
- Read current behavior from matching code/tests before making factual claims.
- Read `../public-repo-safety/SKILL.md` before promoting local screenshots or draft assets into repo-bound public docs.
- Read `../release-docs/SKILL.md` when public wording and repo docs alignment matter.
- Read `../release-verification/SKILL.md` when the user wants fresh screenshots, browser proof, or release-time verification while drafting.
- Read `../autorelease-handoff/SKILL.md` when the posts should be synced into the private `autorelease` repo, especially before branch wrap-up, PR merge, or tagging.
- Read only the reference file for the selected mode:
  - `references/development-log-style.md`
  - `references/release-note-style.md`
  - `references/user-guide-style.md`
- If a repo-tracked development note already exists for the target version, read it before drafting a development log.

## Mode Selection

Choose one mode first.

- `개발 일지`
  Use for version work retrospectives, design notes, why a release was built,
  what changed, and what comes next.
- `릴리즈 노트`
  Use for public release summaries, included features, usage snippets,
  limitations, and supported behavior.
- `사용 가이드`
  Use for current-implementation guidance, supported capabilities,
  execution steps, and stable user-facing explanations.

If the user does not clearly specify the mode, ask one short question.

## Workflow

1. Ground the post in repo truth.
- Take the default version from `pyproject.toml`.
- Take the default date from the local environment.
- Cross-check product claims against code, tests, `README.md`, and examples.
- For `사용 가이드`, use the current branch implementation, not the latest stable tag by default.

2. Apply the selected style reference.
- Keep the structure and tone consistent with the chosen mode.
- Summarize the style pattern; do not copy source articles verbatim.
- Do not append WordPress site chrome such as share buttons, comment blocks, or subscription UI.
- When the current public deployment is part of the reader journey, use the tracked
  server info from `docs/deployment/public-service-info.yaml` rather than
  inventing or paraphrasing URLs from memory.

3. Keep public text product-facing.
- Do not mention bootstrap rules, internal skill routing, or hidden process notes.
- Do not mention AI collaboration unless the repo-tracked development record makes it part of the real story and the mode is `개발 일지`.
- Do not present roadmap items as already implemented behavior.

4. Follow fixed output defaults.
- Output full publishable Markdown by default: title, intro, section headings,
  bullets or code blocks when needed, and a closing paragraph.
- Do not add YAML frontmatter unless the user explicitly asks for it.
- Use mode-specific language defaults unless the user explicitly asks otherwise:
  - `개발 일지` -> Korean
  - `릴리즈 노트` -> English
  - `사용 가이드` -> English
- Save to a `.md` file only when the user clearly asks for file output or gives a path.

5. Hand off branch-ready posts when appropriate.
- `docs/posts/` is the local staging area, not the final publishing repository.
- Keep versioned Markdown source files under `docs/posts/` repo-tracked so post wording changes travel with the implementation they describe.
- Keep versioned screenshot capture folders under `docs/posts/*-image-v*/` local-only unless a reusable asset is intentionally promoted into `docs/shared-assets/`.
- If the user is wrapping up a branch or preparing a version handoff, run `autorelease-handoff` after the posts are ready.
- Prefer the automated handoff script over manual copy/paste so the `autorelease` contract and asset paths stay consistent.

## Mode Requirements

### 개발 일지

- Use a reflective, explanatory tone.
- Default to Korean.
- Start with why this version mattered before listing changes.
- Prefer short paragraphs over long checklists.
- Allow a few focused bullets for concrete accomplishments or next steps.
- Include implementation context only when it helps explain product progress.

### 릴리즈 노트

- Use a contract-style structure.
- Default to English for external readers.
- Include release date, included capabilities, basic usage, current limits, and next steps.
- Include a short `## Live service` section near the top when the release is
  meant to drive readers to the current public site or hosted demo.
- Prefer clear bullets over narrative digressions.
- Distinguish implemented behavior from planned follow-up work.
- When practical, prefer claims backed by a fresh verification pass from `release-verification`.

### 사용 가이드

- Use a stable, instructional tone.
- Default to English for external readers.
- Explain what the product is, what the current version can do, and how to run it.
- Start the guide with a short direct-link section near the top using the
  tracked public server info so readers can open the hosted demo immediately
  without scrolling through a separate `## Live service` block.
- Keep the guide grounded in the current repo implementation.
- Do not turn future roadmap ideas into present-tense guidance.
- When possible, include or reference a real generated `.pptx` result so readers can see the expected output shape.
- If the guide includes both CLI and homepage/web demo commands, place the sample result below the homepage/web demo command section rather than below the CLI command section.
- Keep that sample result near the end of the guide, after the reader has seen how to run the homepage/web demo.
- Prefer sharing the result as a release asset, hosted download, or screenshot reference rather than committing generated files into `output/`.
- When the user wants a screenshot-backed guide, capture the image through `release-verification` first and then write around the verified artifact.
- When the guide explains the "paste the starter YAML into another AI" step, reuse the tracked static insert screenshots under `docs/shared-assets/user-guide-ai-insert/` instead of recapturing provider UI images for each release.

## Output Contract

- State which mode was used when summarizing the work.
- State the language when it differs from the mode default.
- Cite repo files or tests when a factual behavior claim is non-obvious.
- Mention any assumption for version/date if the user did not specify them.
- Keep the final Markdown ready to paste into WordPress without extra wrapper text.

## Resources

- `references/development-log-style.md`
- `references/release-note-style.md`
- `references/user-guide-style.md`
