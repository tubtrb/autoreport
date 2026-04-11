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
- Read `../../../autoreport/web/app.py` when the checker or starter prompt changed.
- Read `../../../autoreport/web/debug_app.py` when the task will surface corpus tables or rerun tools in the debug app.
- Read `../../../tests/test_web_app.py` before claiming the checker contract.
- Read `../../../tests/test_web_debug_app.py` if the debug app UI or API will change.
- Read `references/chatgpt-product-full-prompt-pack.json` when collecting or comparing the default ChatGPT prompt pack.
- If the task is specifically to prove manual YAML auto-repair after a web/server change, also read `../manual-yaml-repair-proof/SKILL.md`.
- Treat `autoreport/web/app.py` as the source of truth for the default production-faithful ChatGPT prompt. Only use synthetic strict/medium/loose/adversarial prompt packs when the task explicitly asks for stress-test variants.
- Use `scripts/collect_chatgpt_corpus.py` when the task needs repeatable ChatGPT batch collection beyond one-off spot tests.
- Use `scripts/run_chatgpt_batch_matrix.ps1` when the task is specifically to run preset count batches such as 20, 30, 40, 50, and 100.
- Use `scripts/export_product_prompt_pack.py` to refresh the default production-faithful prompt pack from `autoreport/web/app.py` before running the default ChatGPT corpus loop.

## Workflow

1. Stabilize the local verifier before sampling.
- Run the narrow web tests first when checker or prompt rules changed:
  `.\venv\Scripts\python.exe -m unittest tests.test_web_app`
- Prefer sampling only after `/api/manual-draft-check` reflects the current rules.
- When the claim is that common AI indentation drift is now recoverable, recheck an existing saved corpus with the current in-process repair path before treating fresh sampling as the only proof.

2. Isolate one provider first.
- Start with one provider, usually ChatGPT, before mixing Gemini or Claude.
- Do not mix providers in the first pass when the goal is to separate
  prompt weakness from provider-specific behavior.

3. Use a fresh chat per sample.
- Never collect a prompt pack in one long conversation thread.
- Open a new chat for each sample so the model does not learn from the
  previous correction or failure.
- If the site requires login or Cloudflare confirmation, let the user
  complete that once, then continue the loop.

4. Use prompt packs instead of one-off prompts.
- Default to the production-faithful pack generated from the full manual prompt comments in `autoreport/web/app.py`.
- Only switch to strict/medium/loose/adversarial synthetic variants when the task explicitly asks for prompt-strength stress testing.
- Keep the chosen pack stable across providers so the comparison is fair.

5. Save every sample as a local artifact set.
- Keep browser artifacts under `output/playwright/`.
- Use a provider-and-pack folder such as
  `output/playwright/chatgpt-pack-03/`.
- For each sample, save:
  - `prompt.txt`
  - `raw-turn.txt`
  - `yaml-candidate.yaml`
  - `checker.json`
- Save pack summaries as `summary.json` and `summary.txt`.
- The bundled collector script also writes `summary.csv` for later debug-app tables.

6. Normalize the captured response before checking it.
- Treat the provider UI text as transport noise.
- Strip visible labels such as `ChatGPT response labels` or `YAML` before
  sending the candidate into the checker.
- When the response includes commentary around the YAML, trim to the first
  `report_content:` block before rerunning `/api/manual-draft-check`.
- Keep the raw unmodified response too; do not overwrite it with the
  normalized candidate.

7. Separate failure classes explicitly.
- Distinguish at least these categories:
  - YAML parse failure
  - no-YAML response, where the model replies with prose or asks for more input instead of returning a YAML draft
  - wrong payload kind, such as `report` instead of `report_content`
  - manual schema-shape drift, such as missing `slots` or `slides`
  - manual pattern-rule failure, such as invented `pattern_id`
  - numbering or style warnings
- Use the checker output as the source of truth for these buckets.

8. Feed summaries into the debug app, not the public app.
- The user app may keep a lightweight checker, but corpus tables, provider
  summaries, and rerun tooling belong in the debug app.
- Keep bulk collection in scripts or terminal loops and let the debug app
  inspect summaries, stored artifacts, and targeted reruns.

## Current Repo Defaults

- The current manual robustness gate is `/api/manual-draft-check` on the
  user web app.
- The starter prompt and checker rules live in `autoreport/web/app.py`.
- The debug app is the right surface for future corpus tables and rerun
  helpers.
- The first provider pass should usually be ChatGPT because it is the
  fastest way to validate the pack and taxonomy before cross-provider work.
- The default bundled ChatGPT prompt pack lives in `references/chatgpt-product-full-prompt-pack.json` and should be refreshed from `autoreport/web/app.py` when the prompt comments change.
- When the local demo server lifecycle is flaky during batch collection, it is acceptable to reuse the same checker logic in-process from `autoreport/web/app.py` instead of depending on an external `http://127.0.0.1:8000/api/manual-draft-check` server.
- After a restarted-server proof, prefer at least one fresh HTTP smoke against the live `/api/manual-draft-check` route before claiming that the server path itself is fixed.

## Output Contract

- State which provider or providers were sampled.
- State how many fresh-chat samples were collected.
- Name the prompt pack or prompt-strength split that was used.
- Give the artifact folder under `output/playwright/`.
- Summarize the dominant failure categories instead of listing raw logs only.
- Call out whether the next step should be prompt tightening, checker
  expansion, or debug-app table work.
