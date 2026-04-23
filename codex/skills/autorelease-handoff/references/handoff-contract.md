# Handoff Contract

This skill treats `docs/posts/` as the local staging area for versioned public
posts and `docs/pages/` as the tracked source of truth for stable standalone
public pages owned by `autoreport`.

The final publishable contract still lives in the private `autorelease`
repository.

## Default file mapping

### Versioned source posts

- `docs/posts/autoreport-v<version>-development-log.md`
  -> `../autorelease/content/devlogs/autoreport-v<version-with-hyphens>-devlog.md`
- `docs/posts/autoreport-guide-v<version>.md`
  -> `../autorelease/content/guides/guide.md`
- `docs/posts/autoreport-v<version>-release-notes.md`
  -> `../autorelease/content/release-notes/autoreport-v<version-with-hyphens>-release-notes.md`

### Stable standalone page sources

- `docs/pages/<slug>.md`
  -> `../autorelease/content/pages/<slug>.md`

Current expected standalone page slugs include:

- `about`
- `contact`
- `privacy`
- `what-autoreport-solves`
- `manual-draft-workflow`
- `draft-checker-and-repair`
- `screenshot-preparation`

The standalone source files above use the publishable page contract directly:
they keep page front matter in-source, set `content_type: page`, and do not use
the `section` field.

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
- Guide source posts should start with a short action-link section near the top
  instead of a separate `## Live service` block.
- Release-note source posts may still keep a `## Live service` section near the
  top when public readers need the current site or hosted demo pointers.
- The automated handoff is allowed to normalize the guide action-link section
  and the homepage or release-note live-service information from the same
  tracked URL source.

## Source ownership and direct-edit rule

- `docs/posts/*.md` is the source of truth for versioned `guide`, `devlog`, and
  `release-note` content before handoff.
- `docs/pages/*.md` is the source of truth for Autoreport-owned standalone
  appendix pages that publish into `../autorelease/content/pages/`.
- When a matching file exists under `docs/pages/*.md`, do not treat the
  corresponding `../autorelease/content/pages/*.md` file as editable source of
  truth. Edit the `autoreport` source file and rerun the handoff instead.
- If an urgent fix is applied directly in `../autorelease/content/pages/*.md`,
  copy that fix back into the matching `docs/pages/*.md` file in the same task.
- `../autorelease/content/pages/main.md` is the homepage exception. This
  handoff only normalizes its shared live-service block and does not make
  `docs/pages/main.md` part of the appendix contract.

## Why the script exists

- `docs/posts/` files are usually plain Markdown, not full publishable handoff items.
- `docs/pages/` files are already publishable page sources and are copied to the
  matching `content/pages/` path rather than being rewritten into a different
  filename contract.
- `autorelease` requires YAML front matter, section-aware paths, and asset-local references.
- The automated handoff keeps those conversions and page copies consistent
  across releases and avoids drift from manual copy/paste.

## Validation strategy

- The script validates only the touched posts by default.
- The script also validates any copied standalone pages.
- This avoids blocking a content handoff because of unrelated uncommitted work elsewhere in `autorelease`.
- If the user wants full publish readiness, run the broader `autorelease` validation flow separately after the handoff.
