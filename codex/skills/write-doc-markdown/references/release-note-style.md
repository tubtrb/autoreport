# Release Note Style

## Purpose

Use this mode for public release notes that communicate what the version
includes, how to use it, and what limits still exist.
Default to English unless the user explicitly asks for another language.

## Structure

- Title in the form `## Autoreport vX.Y.Z Release Notes`
- `Release date: ...` near the top
- Short intro paragraph about the release goal
- `## Live service` near the top when the release note should point readers to
  the current public site or hosted demo
- `## What's included in this release`
- `## Basic usage`
- `## Supported input structure` when schema details matter
- `## Output format` or another output-contract section when relevant
- `## Error handling` and/or `## Current limitations`
- `## Next steps`

## Tone

- Prefer concise, contract-style explanations.
- Use bullets for supported features, limitations, and option lists.
- Keep paragraphs short and operational.
- Make it easy to scan for what is supported today.
- Write in clear product English rather than literal translation from Korean.

## Content Rules

- Separate implemented behavior from future work.
- Include commands only when they match the current repo behavior.
- When the release is already publicly hosted, read
  `docs/deployment/public-service-info.yaml` and use those exact URLs in the
  live-service block.
- Include limitations when the implementation is intentionally narrow.
- Do not oversell roadmap items or imply unsupported flexibility.

## Formatting

- No YAML frontmatter by default.
- Use fenced code blocks for commands and literal output-path examples.
- Keep bullet density moderate and grouped by section.
