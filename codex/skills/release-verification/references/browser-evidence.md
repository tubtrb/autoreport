# Browser Evidence

## Artifact Goals

Capture evidence that is directly reusable in release communication:

- one clean homepage capture
- one success-state capture after generation
- browser name used for the capture
- proof that the download event fired

## Preferred Locations

- screenshots: `output/playwright/`
- temporary logs: `tests/_tmp/`
- Playwright downloads: `.playwright-cli/` or the configured Playwright artifact directory

Do not commit generated files from `output/` by default.

## Suggested Naming

Use names that preserve version and browser context, for example:

- `output/playwright/homepage/autoreport-v0.2.1-homepage-full.png`
- `output/playwright/homepage/autoreport-v0.2.1-chrome-success-full.png`
- `output/playwright/homepage/autoreport-v0.2.1-edge-success-full.png`

## What To Mention In Summaries

- browser: `msedge` or `chrome`
- route exercised: usually `http://127.0.0.1:8000/`
- whether example loading was used
- whether `weekly_report.pptx` download was observed
- whether the visible success state matched the current UI copy

## Promotion Rule

Keep raw verification artifacts in `output/` first.

Only move or duplicate an image into a docs-facing location when the user
explicitly wants a curated asset for a guide, release note, or WordPress post.
