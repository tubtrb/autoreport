# Autoreport Architecture Docs

This folder documents the current `autoreport` core from a testing-first point of view.
It is meant to help contributors inspect the live design without relying on a GUI.

```mermaid
flowchart TD
    README["Architecture index"]
    OVERVIEW["System overview"]
    CLISEQ["CLI sequence"]
    WEBSEQ["Web demo sequence"]
    FLOW["Generation flow"]
    AUTOFILL["Template-aware autofill engine"]
    ERRORS["Error and validation map"]
    TESTMAP["Feature to test map"]
    CONTRACT["Weekly report contract"]

    README --> OVERVIEW
    README --> CLISEQ
    README --> WEBSEQ
    README --> FLOW
    README --> AUTOFILL
    README --> ERRORS
    README --> TESTMAP
    README --> CONTRACT
```

Start here when you need to understand how the current weekly report pipeline is wired.
Read `system-overview.md` first, then pick the sequence, flow, contract, or test map that matches the feature you are touching.

## Document set

- `system-overview.md`: high-level component view of the current runtime path
- `cli-sequence.md`: end-to-end CLI generation path and failure mapping
- `web-demo-sequence.md`: browser-to-API generation path and HTTP outcomes
- `generation-flow.md`: data-shape transitions from YAML input to `.pptx`
- `template-aware-autofill-engine.md`: near-term `v0.3` direction for profiling templates, slot mapping, fitting, and diagnostics
- `error-and-validation-map.md`: shared failure boundaries and surface-specific responses
- `feature-test-map.md`: feature ownership mapped to current unittest modules
- `weekly-report-contract.md`: current input contract and validation rules

## Inspection points

- Treat repository code and tests as the source of truth when these docs drift.
- The current product has two entry points, but both converge on the same weekly generation core.
- The current scope is deterministic weekly report generation only.
- `autorelease`, WordPress publishing, and private workflow steps are intentionally out of scope here.

## Source of truth

- `README.md`
- `pyproject.toml`
- `autoreport/cli.py`
- `autoreport/web/app.py`
- `tests/`
