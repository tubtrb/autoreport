# User Guide Style

## Purpose

Use this mode for current-implementation guidance that helps a user
understand what Autoreport is, what the current version can do,
and how to run it.
Default to English unless the user explicitly asks for another language.

## Structure

- Title `# User Guide`
- `Current version: ...` near the top
- Intro that defines the guide as the current implementation reference
- `## Live service` near the top when the public site or hosted demo should be
  directly usable by readers
- `## What is Autoreport?`
- `## What the current version can do`
- `## Basic usage`
- If both CLI and homepage/web demo commands are present, place the sample-output section below the homepage/web demo command block
- End the guide with a short sample-output section so readers can immediately open a real generated `.pptx` after seeing how to run the homepage/web demo
- Additional sections only when they clarify real current behavior

## Tone

- Prefer stable, instructional prose.
- Keep explanations simple and grounded in present-tense behavior.
- Use bullets for supported capabilities and slide/output structure.
- Avoid release-process narration or roadmap-heavy copy.
- Write in direct, readable product English for external readers.

## Content Rules

- Use the current branch implementation by default.
- Describe only what is demonstrably supported by code/tests/docs.
- When the guide is meant for `autorelease`, read
  `docs/deployment/public-service-info.yaml` and use those exact URLs in the
  `## Live service` block instead of route-only placeholders.
- Mention where users can check version-specific changes if that context helps.
- Do not write speculative setup or future features as if they exist now.
- Prefer showing or linking to an actual generated `.pptx` result in the published guide because it makes the output concrete for new readers.
- In the final layout, keep the sample `.pptx` link or screenshot below the homepage/web demo command examples rather than near the top of the page.
- Do not assume generated files should be committed to the repository; prefer hosted artifacts, release assets, or screenshots unless the user explicitly wants a repo-tracked sample in another safe location.
- When the guide documents the external-AI drafting handoff, reuse the tracked insert screenshots under `docs/shared-assets/user-guide-ai-insert/` rather than taking new provider UI captures for each version.

## Formatting

- No YAML frontmatter by default.
- Use fenced code blocks for commands.
- Keep the guide concise enough to read as a living reference page.
