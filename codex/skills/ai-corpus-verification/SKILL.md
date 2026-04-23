---
name: ai-corpus-verification
description: Collect and analyze real external-AI draft corpora for autoreport's manual YAML flow. Use when Codex needs repeated ChatGPT, Gemini, or Claude spot tests, prompt-pack comparisons, `/api/manual-draft-check` reruns, failure taxonomy capture, or debug-app corpus tables that summarize which prompts or providers break the manual contract.
---

# AI Corpus Verification

## Overview

Use this skill when the task is not just "does the web app work" but
"how do real external AIs behave against our manual YAML rules over many
samples?" Keep the collection loop provider-aware, checker-driven, and
artifact-backed so the results can feed a debug surface later.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../web-demo/SKILL.md`.
- Read `../../../docs/architecture/verif_test/02_prompt_yaml_generation.md`.
- Read `../../../docs/architecture/verif_test/03_ai_batch_run_logging.md`.
- Read `../../../docs/architecture/verif_test/04_result_review_gate.md`.
- Read `../../../autoreport/web/app.py` when the checker or starter prompt changed.
- Read `../../../autoreport/web/debug_app.py` when the task will surface corpus tables or rerun tools in the debug app.
- Read `../../../tests/test_web_app.py` before claiming the checker contract.
- Read `../../../tests/test_web_debug_app.py` if the debug app UI or API will change.
- Read `references/chatgpt-product-full-prompt-pack.json` when collecting or comparing the default ChatGPT prompt pack.
- If the task is specifically to prove manual YAML auto-repair after a web/server change, also read `../manual-yaml-repair-proof/SKILL.md`.
- Treat `autoreport/web/app.py` as the source of truth for the default production-faithful ChatGPT prompt. Only use synthetic strict/medium/loose/adversarial prompt packs when the task explicitly asks for stress-test variants.
- Use `..\..\..\run_manual_ai_regression.ps1` as the canonical operator entrypoint for suite-based public-manual diagnostics and spot checks.
- Use `..\..\..\run_manual_ai_release_gate.ps1` only when the task is explicitly the official low-trigger ChatGPT web release gate.
- Treat the ChatGPT transport as an attach-only controller over a user-opened Chrome session.
- Canonical session key: `extai-chatgpt-spot`.
- Canonical persistent profile path: `.codex\playwright\profiles\extai-chatgpt-spot`.
- Remembered last-success URL path: `.codex\playwright\extai-chatgpt-spot-last-url.txt`.
- Legacy one-time recovery source: `output\playwright\chrome-userdata-copy`.
- Treat `scripts/collect_chatgpt_corpus.py` as a compatibility wrapper over `tests/verif_test` when the task needs prompt-pack driven collection beyond one-off spot tests.
- Use `scripts/run_chatgpt_batch_matrix.ps1` only for diagnostic or stress sampling such as preset 20, 30, 40, 50, and 100 loops. It is not the release-gate operator flow.
- Use `scripts/export_product_prompt_pack.py` to refresh the default production-faithful prompt pack from the tracked `tests/verif_test/cases/manual_public_cases.yaml` plus `autoreport/web/app.py` prompt header before running the default ChatGPT corpus loop.

## Workflow

1. Stabilize the local verifier before sampling.
- Run the narrow web tests first when checker or prompt rules changed:
  `.\venv\Scripts\python.exe -m unittest tests.test_web_app tests.test_web_serve`
- Prefer sampling only after `/api/manual-draft-check` reflects the current rules.
- When the claim is that common AI YAML drift is now recoverable, recheck an existing saved corpus with the current in-process extraction and repair path before treating fresh sampling as the only proof.

2. Isolate one provider first.
- Start with one provider, usually ChatGPT, before mixing Gemini or Claude.
- Do not mix providers in the first pass when the goal is to separate
  prompt weakness from provider-specific behavior.

3. Use a fresh chat per sample unless the task is explicitly the release gate.
- Never collect a prompt pack in one long conversation thread.
- Open a new chat for each sample so the model does not learn from the
  previous correction or failure.
- The official release gate is the deliberate exception: it uses one seeded
  browser session, one selected ChatGPT page, fixed chunks, and paced cooldowns
  through `run_manual_ai_release_gate.ps1`.
- Do not let the runner launch or relaunch Chrome. It must attach only to the
  already-open manual Chrome session and then pick the best ready `chatgpt.com`
  page from the pages that user session already has open.
- If the profile is cold or Cloudflare/login is expected, first guide the user
  to open the canonical profile manually from a regular terminal-launched Chrome
  session with the attach port:

```powershell
$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
  $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}
$profile = Join-Path (Get-Location) ".codex\playwright\profiles\extai-chatgpt-spot"
& $chrome --remote-debugging-port=9222 --user-data-dir="$profile" "https://chatgpt.com/"
```

- Tell the user to complete login or challenge there, open one real ChatGPT
  conversation, optionally send one short message, and keep that Chrome window
  open before any runner command starts.

Before any smoke or corpus run, use the canonical validator:

```powershell
powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
```

Use `-SessionCheckOnly` only after the manual terminal-open seed step above has
finished. Treat it as an attach/readiness verifier, not the primary login flow.

For the official low-trigger release gate, validate the same seeded profile and
then run the dedicated wrapper:

```powershell
powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http
```

4. Use prompt packs instead of one-off prompts.
- Default to the production-faithful pack generated from the full manual prompt comments in `autoreport/web/app.py`.
- Only switch to strict/medium/loose/adversarial synthetic variants when the task explicitly asks for prompt-strength stress testing.
- Keep the chosen pack stable across providers so the comparison is fair.

5. Save every sample as a local artifact set.
- Keep run artifacts under `output/verif_test/<run-id>/`.
- Use the fixed root summary files from the canonical runner:
  - `run-config.json`
  - `events.jsonl`
  - `session-check.json`
  - `session-check.md`
  - `session-page.txt`
  - `session-network.jsonl`
  - `summary.json`
  - `summary.csv`
  - `summary.md`
  - `review-queue.json`
  - `review-queue.md`
- For each sample, save:
  - `starter.yaml`
  - `prompt.txt`
  - `case-manifest.json`
  - `ai-raw.txt`
  - `raw-turn.txt`
  - `yaml-candidate.yaml`
  - `checker.json`
  - `generate.json`
  - `pptx-inspection.json`
  - `artifact.pptx`
  - `transport-state.json`
  - `transport-network.jsonl`
  - `transport-console.jsonl`
- The bundled collector wrapper and canonical runner both write the root summaries for later debug-app tables.

6. Normalize the captured response before checking it.
- Treat the provider UI text as transport noise.
- Strip visible labels such as `ChatGPT response labels` or `YAML` before
  sending the candidate into the checker.
- When the response includes commentary around the YAML, trim to the first
  `report_content:` block before rerunning `/api/manual-draft-check`.
- Keep the raw unmodified response too; do not overwrite it with the
  normalized candidate.

7. Separate failure classes explicitly.
- Use the canonical hard-failure taxonomy from `docs/architecture/verif_test/03_ai_batch_run_logging.md`:
  - `ai_transport_failure`
  - `yaml_extract_failure`
  - `checker_failure`
  - `generate_failure`
  - `pptx_inspection_failure`
- Use the checker or generate output as the source of truth for these buckets.

8. Feed summaries into the debug app, not the public app.
- The user app may keep a lightweight checker, but corpus tables, provider
  summaries, and rerun tooling belong in the debug app.
- Keep bulk collection in scripts or terminal loops and let the debug app
  inspect summaries, stored artifacts, and targeted reruns.

## Current Repo Defaults

- The current manual robustness gate is `/api/manual-draft-check` on the
  user web app.
- The starter prompt and checker rules live in `autoreport/web/app.py`.
- The tracked suite and case source of truth lives in `tests/verif_test/cases/manual_public_cases.yaml`.
- The debug app is the right surface for future corpus tables and rerun
  helpers.
- The default bundled ChatGPT prompt pack should mirror the full public
  manual starter prompt, including the task line and complete `report_content`
  YAML body.
- The first provider pass should usually be ChatGPT because it is the
  fastest way to validate the pack and taxonomy before cross-provider work.
- The default bundled ChatGPT prompt pack lives in `references/chatgpt-product-full-prompt-pack.json` and should be refreshed from `autoreport/web/app.py` when the prompt comments change.
- The canonical runner emits `PASS`, `FAIL`, or `REVIEW` at the run level and uses a fixed representative review queue instead of dynamic sampling.
- The canonical runner must not launch, close, or restart Chrome. It attaches to
  the named canonical profile only after the user has opened Chrome manually
  with the attach port.
- `-SessionCheckOnly` attaches to the already-open Chrome window and validates
  both DOM readiness and recent network failures before case execution. It
  should follow the manual terminal-open profile-seed flow when the profile is
  cold or recently challenge-blocked.
- The canonical runner rejects `--no-sandbox`, in-memory profiles, and wrong-profile launches before case execution and writes `session-check.json` plus `session-check.md`.
- Root and per-case summaries expose `transport_attempts`, `session_relaunches`, `selected_page_url`, `recent_response_failures`, and `no_sandbox_detected`.
- The low-trigger release gate adds `runbook`, `planned_chat_count`,
  `completed_chat_count`, `chunk_results`, `cooldown_schedule_applied`,
  `guard_trip_reason`, `guard_trip_stage`, and
  `single_session_browser_relaunches`.
- In the release gate, `single_session_browser_relaunches` must remain `0`
  after bootstrap. If challenge or auth signals appear mid-run, the correct
  outcome is clear failure and stop, not more aggressive retries.
- When the local demo server lifecycle is flaky during batch collection, it is acceptable to reuse the same checker logic in-process from `autoreport/web/app.py` instead of depending on an external `http://127.0.0.1:8000/api/manual-draft-check` server.
- After a restarted-server proof, prefer at least one fresh HTTP smoke against the live `/api/manual-draft-check` route before claiming that the server path itself is fixed.

## Output Contract

- State which provider or providers were sampled.
- State how many fresh-chat samples were collected.
- Name the prompt pack or prompt-strength split that was used.
- Give the artifact folder under `output/verif_test/`.
- Summarize the dominant failure categories instead of listing raw logs only.
- Call out whether the next step should be prompt tightening, checker
  expansion, or debug-app table work.
