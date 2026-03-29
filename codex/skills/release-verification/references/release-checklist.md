# Release Checklist

## Purpose

Use this checklist when verifying a release candidate or when public docs should
be backed by fresh proof from the current branch.

## Default Sequence

1. Confirm the target version from `pyproject.toml`.
2. Decide which claims are being signed off on.
3. Run the narrowest relevant tests first.
4. Confirm `/healthz` for the web demo when web release readiness matters.
5. Reproduce the main user flow in a browser.
6. Capture at least one artifact that shows the visible state the docs will describe.
7. Summarize what passed, what was not checked, and what still looks risky.

## Web Demo Minimum Bar

For the current `v0.3.x` web demo, the minimum browser signoff should include:

- homepage loads at `/`
- demo title is visible
- starter YAML is present
- generating the deck triggers `autoreport_demo.pptx`
- success-state copy is visible after generation

## Cross-Browser Rule

When multiple Chromium-based browsers are available on Windows:

- run one smoke check in `msedge`
- run one cross-check in `chrome`

If one browser is missing, say so explicitly instead of implying cross-browser coverage.

## Doc Handoff Rule

When release notes or a guide are created from the same session:

- prefer claims that were just re-verified
- mention the verification basis when it matters
- attach screenshot paths or public URLs for assets that will be reused
- keep roadmap statements out of the verified behavior section
