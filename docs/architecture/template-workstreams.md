# Template Workstreams

This note defines the current versioned parallel work split for the contract-first
Autoreport product line when one version-master line is being developed in
multiple worktrees.
It is contributor-facing planning guidance, not public product copy.

## Why this file exists

The target runtime flow is:

1. user inspects a built-in or user-supplied PowerPoint template
2. `autoreport` exports the matching template contract
3. a human or another AI fills `report_content` or `authoring_payload`
4. `autoreport` generates an editable `.pptx`

That product surface is broad enough to benefit from parallel work, but the
parallelism must stay aligned around one shared integration branch and one
shared contract model.

## Branch strategy

- Integration base branch: `codex/v<version>-master`
- Task branches branch from that base and merge back into that base.
- The active task branches are intentionally horizontal, for example:
  - `codex/v<version>-contract-hardening`
  - `codex/v<version>-web-authoring-ux`
  - `codex/v<version>-generation-preview`
  - `codex/v<version>-release-prep`
- Maintenance or integration-support branches such as
  `codex/v<version>-bootstrap-*` and `codex/v<version>-salvage-*` are not treated as active
  workstreams for orchestration purposes
- The workstream-orchestrator defaults should infer the active `<version>` from the
  checked-out `codex/v<version>-master` branch when possible, or else from the
  highest discovered version-master branch in the repo.

## Shared guardrails

- Treat repository code and tests as the source of truth
- Preserve the current CLI and web error contracts unless a task branch
  explicitly owns them
- Keep tasks horizontal: one cross-cutting concern per branch
- Do not split work by arbitrary line ranges in the same file
- If a task branch introduces a new shared contract field or pattern, document
  it in code/tests before asking another branch to depend on it

## Shared target contracts

All task branches should align around these public shapes unless the
integration owner deliberately changes them:

```yaml
template_contract:
  contract_version: autoreport.template.v1
  template_id: string
  template_label: string
  template_source: built_in | uploaded
  title_slide:
    pattern_id: string
    layout_name: string
    slots:
      - slot_id: string
        alias: string
        slot_type: title | text
        required: true | false
  contents_slide:
    pattern_id: string
    layout_name: string
    slots:
      - slot_id: string
        alias: string
        slot_type: title | text
        required: true | false
  slide_patterns:
    - pattern_id: string
      kind: text | metrics | text_image
      layout_name: string
      slots:
        - slot_id: string
          alias: string
          slot_type: title | text | image | caption
          required: true | false
          orientation: stack | vertical | horizontal
          order: integer
```

```yaml
report_payload:
  payload_version: autoreport.payload.v1
  template_id: string
  title_slide:
    title: string
    subtitle:
      - string
  contents:
    enabled: true | false
  slides:
    - kind: text | metrics | text_image
      pattern_id: string
      title: string
      include_in_contents: true | false
      body:
        - string
      items:
        - label: string
          value: string | integer
      image:
        path: string
        ref: string
        fit: contain | cover
      caption: string
      slot_overrides: {}
```

## Contract ownership

- `codex/v<version>-contract-hardening` owns exported contract shape, payload shape,
  validation strictness, and example fixture clarity
- `codex/v<version>-web-authoring-ux` owns how the contract and payload are shown and
  edited in the web surface
- `codex/v<version>-generation-preview` owns how payload content lands in profiled
  slots and how generation evidence is surfaced
- `codex/v<version>-release-prep` owns release-facing wording, package/release docs,
  and user-facing examples once behavior is confirmed

## Active workstreams

### 1. Contract Hardening

- Branch pattern: `codex/v<version>-contract-hardening`
- Owns:
  - contract export shape stability
  - payload validation rules
  - slot override rules
  - example payload and contract fixtures
- Main files:
  - `autoreport/template_flow.py`
  - `autoreport/models.py`
  - `autoreport/validator.py`
  - `tests/test_loader.py`
  - `tests/test_validator.py`
  - `tests/test_cli.py` when CLI contract wiring changes
- Verification:
  - `.\venv\Scripts\python.exe -m unittest tests.test_loader tests.test_validator`

### 2. Web Authoring UX

- Branch pattern: `codex/v<version>-web-authoring-ux`
- Owns:
  - contract panel readability
  - payload editing helpers
  - image upload to `image_*` ref workflow
  - deck-summary and status feedback in the demo
- Main files:
  - `autoreport/web/app.py`
  - `tests/test_web_app.py`
- Verification:
  - `.\venv\Scripts\python.exe -m unittest tests.test_web_app`

### 3. Generation Preview

- Branch pattern: `codex/v<version>-generation-preview`
- Owns:
  - text/image slot landing quality
  - continuation and spill behavior
  - caption pairing and image safety
  - generation evidence that can back lightweight previews or summaries
- Main files:
  - `autoreport/templates/autofill.py`
  - `autoreport/templates/weekly_report.py`
  - `autoreport/engine/generator.py`
  - `autoreport/outputs/pptx_writer.py`
  - `tests/test_autofill.py`
  - `tests/test_generator.py`
  - `tests/test_pptx_writer.py`
- Verification:
  - `.\venv\Scripts\python.exe -m unittest tests.test_autofill tests.test_generator tests.test_pptx_writer`

### 4. Release Prep

- Branch pattern: `codex/v<version>-release-prep`
- Owns:
  - `README.md`
  - `pyproject.toml`
  - architecture and release-facing docs
  - release checklist wording and example usage
- Verification:
  - narrow tests depend on the touched runtime surface
  - run at least `tests.test_cli` and `tests.test_web_app` when public usage or
    wording depends on observed behavior

## Merge order

1. `codex/v<version>-contract-hardening`
2. `codex/v<version>-generation-preview`
3. `codex/v<version>-web-authoring-ux`
4. `codex/v<version>-release-prep`

`generation-preview` and `web-authoring-ux` may proceed in parallel, but
`contract-hardening` should freeze shared field names and slot rules first.

## Orchestration model

- The workstream-orchestrator should not rely on a fixed list of sibling
  folders.
- Instead, it should discover active task worktrees from `git worktree list`
  and treat branches under the active `codex/v<version>-*` line as candidates.
- Integration/maintenance branches such as `codex/v<version>-master`,
  `codex/v<version>-bootstrap-*`, and `codex/v<version>-salvage-*` are excluded from the
  active task list by default.
- Each active task worktree may optionally define local orchestration metadata
  in `.codex/workstream.json`, such as:
  - `key`
  - `test_modules`
  - `orchestration_enabled`

## Thread handoff checklist

Each task branch should close only after it can answer "yes" to all of these:

- Is the owned interface documented in code or tests?
- Are the narrow verification commands passing?
- Are unrelated files left alone?
- Is `codex/v<version>-master` still the correct merge target?
- Did the branch avoid changing public wording unless it owned the flow?
