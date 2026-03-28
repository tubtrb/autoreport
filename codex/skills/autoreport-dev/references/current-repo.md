# Current Repo

## Project Shape

- `autoreport` currently packages a deterministic weekly report generator.
- Package metadata and the current version live in `pyproject.toml`; treat that file as the source of truth instead of copying version numbers into skill docs.
- Public entry points are the `autoreport` CLI and the FastAPI demo app in `autoreport/web/app.py`.

## Behavior Sources

- `tests/test_cli.py` locks the CLI success line and failure mapping.
- `tests/test_loader.py` and `tests/test_validator.py` lock loader and schema behavior.
- `tests/test_generator.py` and `tests/test_pptx_writer.py` lock generation and template compatibility behavior.
- `tests/test_web_app.py` locks the web HTML surface, healthcheck, JSON error shapes, and PPTX download response.

## Main Code Paths

- `autoreport/cli.py` builds the parser and maps exceptions to exit codes and stderr text.
- `autoreport/engine/generator.py` loads raw YAML, validates it, builds template context, and writes the `.pptx`.
- `autoreport/outputs/pptx_writer.py` loads a template or default presentation, validates layout compatibility, clears seed slides, and writes slides.
- `autoreport/web/app.py` reuses the same core parse/validate/generate flow for the public demo API.

## Shared Guardrails

- Keep `codex/skills/` as the shared bootstrap layer.
- Keep `.codex/` as private/local state.
- Do not present roadmap items as already implemented behavior.
