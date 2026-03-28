# Development Log Style

## Purpose

Use this mode for version retrospectives and public development notes.
The post should explain why a version mattered, what was built, and
how the work changed the product's direction.
Default to Korean unless the user explicitly asks for another language.

## Structure

- Title in the form `## Autoreport vX.Y.Z 개발 일지`
- Opening paragraph that frames the version and its intent
- `## 이번 버전에서 한 일`
- `## 왜 이 작업을 먼저 했는가` or another rationale section
- Optional implementation deep-dive sections when they explain visible progress
- `## 현재 상태`
- `## 다음 단계`

## Tone

- Prefer reflective prose over dense bullet lists.
- Keep the writing calm, concrete, and product-oriented.
- Use bullets sparingly for grouped accomplishments or next steps.
- Explain decisions and tradeoffs, not just feature names.

## Content Rules

- Use repo-tracked facts, tests, and docs as the source of truth.
- Mention development process details only when they are part of the actual repo history for that version.
- Avoid internal bootstrap talk, hidden prompting, or tool orchestration details.
- Do not end the post like a checklist; close with what the version means for the product.

## Formatting

- No YAML frontmatter by default.
- Use standard fenced code blocks for commands.
- Keep sections in Markdown heading form only; do not include WordPress share/footer UI.
