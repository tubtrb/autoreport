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
- Read current behavior from matching code/tests before making factual claims.
- Read `../public-repo-safety/SKILL.md` before promoting local screenshots or draft assets into repo-bound public docs.
- Read `../release-docs/SKILL.md` when public wording and repo docs alignment matter.
- Read `../release-verification/SKILL.md` when the user wants fresh screenshots, browser proof, or release-time verification while drafting.
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
- Prefer clear bullets over narrative digressions.
- Distinguish implemented behavior from planned follow-up work.
- When practical, prefer claims backed by a fresh verification pass from `release-verification`.

### 사용 가이드

- Use a stable, instructional tone.
- Default to English for external readers.
- Explain what the product is, what the current version can do, and how to run it.
- Keep the guide grounded in the current repo implementation.
- Do not turn future roadmap ideas into present-tense guidance.
- When possible, include or reference a real generated `.pptx` result so readers can see the expected output shape.
- If the guide includes both CLI and homepage/web demo commands, place the sample result below the homepage/web demo command section rather than below the CLI command section.
- Keep that sample result near the end of the guide, after the reader has seen how to run the homepage/web demo.
- Prefer sharing the result as a release asset, hosted download, or screenshot reference rather than committing generated files into `output/`.
- When the user wants a screenshot-backed guide, capture the image through `release-verification` first and then write around the verified artifact.

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
