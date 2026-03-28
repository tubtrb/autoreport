# Current Repo

## Project Shape

- `autoreport` currently packages a deterministic contract-first PowerPoint deck generator.
- Package metadata and the current version live in `pyproject.toml`; treat that file as the source of truth instead of copying version numbers into skill docs.
- Public entry points are the `autoreport` CLI, the user-facing FastAPI app in `autoreport/web/app.py`, and the developer-facing debug FastAPI app in `autoreport/web/debug_app.py`.

## Behavior Sources

- `tests/test_cli.py` locks the CLI success line and failure mapping.
- `tests/test_loader.py` and `tests/test_validator.py` lock loader and schema behavior.
- `tests/test_generator.py` and `tests/test_pptx_writer.py` lock generation and template compatibility behavior.
- `tests/test_web_app.py` locks the user-facing web HTML surface, healthcheck, JSON error shapes, and PPTX download response.
- `tests/test_web_debug_app.py` locks the separate debug app surface and confirms it stays wired to the shared compile/generate routes.

## Main Code Paths

- `autoreport/cli.py` builds the parser and maps exceptions to exit codes and stderr text.
- `autoreport/template_flow.py` exports template contracts and starter payloads.
- `autoreport/engine/generator.py` loads raw YAML, validates it, builds template context, and writes the `.pptx`.
- `autoreport/outputs/pptx_writer.py` loads a template or default presentation, validates layout compatibility, clears seed slides, and writes slides.
- `autoreport/web/app.py` is the simplified user-facing web app for the "copy AI package, paste draft, generate" flow.
- `autoreport/web/debug_app.py` is the developer-facing debug surface for contract, normalization, compiled payload, and upload inspection on top of the same shared API routes.

## Shared Guardrails

- Keep `codex/skills/` as the shared bootstrap layer.
- Keep `.codex/` as private/local state.
- Do not present roadmap items as already implemented behavior.
