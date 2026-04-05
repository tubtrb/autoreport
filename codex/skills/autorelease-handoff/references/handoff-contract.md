# Handoff Contract

This skill treats `docs/posts/` as the local staging area for versioned public posts.
The final publishable contract lives in the private `autorelease` repository.

## Default file mapping

- `docs/posts/autoreport-v<version>-development-log.md`
  -> `../autorelease/content/devlogs/autoreport-v<version-with-hyphens>-devlog.md`
- `docs/posts/autoreport-guide-v<version>.md`
  -> `../autorelease/content/guides/guide.md`
- `docs/posts/autoreport-v<version>-release-notes.md`
  -> `../autorelease/content/release-notes/autoreport-v<version-with-hyphens>-release-notes.md`

## Default asset mapping

- `docs/posts/devlog-image-v<version>/`
  -> `../autorelease/content/assets/autoreport-v<version-with-hyphens>-devlog/`
- `docs/posts/guide-image-v<version>/`
  -> `../autorelease/content/assets/guide/`
- `docs/shared-assets/user-guide-ai-insert/`
  -> `../autorelease/content/assets/guide/ai-insert/`

The guide path is intentionally stable because `autorelease` publishes the main
user guide at `/guide/` and updates that page in place across releases.

## Live service synchronization

- The tracked source of public server URLs is
  `docs/deployment/public-service-info.yaml` in the `autoreport` repository.
- Guide and release-note source posts should keep a `## Live service` section
  near the top when they are meant for public readers.
- The automated handoff is allowed to normalize that block so the stable guide
  page and `../autorelease/content/pages/main.md` use the same live service
  information.

## Why the script exists

- `docs/posts/` files are usually plain Markdown, not full publishable handoff items.
- `autorelease` requires YAML front matter, section-aware paths, and asset-local references.
- The automated handoff keeps those conversions consistent across releases and avoids drift from manual copy/paste.

## Validation strategy

- The script validates only the touched posts by default.
- This avoids blocking a content handoff because of unrelated uncommitted work elsewhere in `autorelease`.
- If the user wants full publish readiness, run the broader `autorelease` validation flow separately after the handoff.
