---
name: manual-yaml-repair-proof
description: Prove Autoreport's manual YAML auto-repair path works after web-app or server changes. Use when Codex changed pre-parse manual draft repair, ChatGPT full-prompt transport, or the manual checker/compile/generate flow and needs saved-corpus salvage plus live post-restart server proof.
---

# Manual YAML Repair Proof

## Overview

Use this skill when the question is not just "did the code change compile" but
"did the real manual-YAML recovery path hold up against actual AI drafts and a
restarted local server?" It standardizes the proof loop for the manual
`report_content` flow.

## Mandatory Preload

- Read `../../../AGENTS.md`.
- Read `../autoreport-dev/SKILL.md`.
- Read `../web-demo/SKILL.md`.
- Read `../ai-corpus-verification/SKILL.md`.
- Read `../../../autoreport/web/app.py` when the parser, checker, starter prompt, or manual flow changed.
- Read `../../../tests/test_web_app.py` and `../../../tests/test_web_serve.py` before claiming the proof is complete.
- Read `references/proof-flow.md`.
- Use `scripts/recheck_manual_corpus.py` to replay saved corpus artifacts through the current in-process repair and checker path.
- Use `scripts/run_server_proof.ps1` to run narrow tests plus a live HTTP smoke against the restarted local server.

## Workflow

1. Prove the code path first.
- Run the narrow web tests:
  `.\venv\Scripts\python.exe -m unittest tests.test_web_app tests.test_web_serve`
- Do not start with corpus claims if the narrow tests are red.

2. Recheck a saved real corpus when claiming recovery.
- Replay an existing artifact folder through the current repair path:
  `.\venv\Scripts\python.exe codex\skills\manual-yaml-repair-proof\scripts\recheck_manual_corpus.py --artifact-dir <output-folder>`
- Use this to measure salvage against real previously captured AI drafts.
- Prefer the most recent production-faithful ChatGPT full-prompt pack when available.

3. Prove the restarted server with a fresh live smoke.
- Refresh the prompt pack from `autoreport/web/app.py`.
- Confirm `/healthz` on the restarted local server.
- Run at least one fresh ChatGPT sample against the HTTP checker path:
  `powershell -File codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 -Session extai-chatgpt-spot -SmokeCount 1`
- When the claim is broader than a local smoke, add a fresh corpus count such as `-CorpusCount 20`.

4. Keep the proof route production-faithful.
- Use the full manual comments exported from `autoreport/web/app.py`, not synthetic strict/medium/loose/adversarial packs, unless the user explicitly asks for stress testing.
- Prefer `--checker-mode http` for the restarted-server proof so the live route is exercised end to end.
- Use in-process recheck only for saved-corpus salvage measurement.

5. Separate the two proof questions.
- "Does the code know how to repair this class of YAML drift?" -> saved corpus recheck.
- "Does the restarted server actually do it on the live path?" -> fresh HTTP smoke or corpus run.
- Do not let one substitute for the other when both are relevant.

## Current Repo Defaults

- The common recovery target is manual `report_content` indentation drift from external AI replies.
- The auto-repair path is expected to run before parse in the manual checker, compile, and generate entrypoints.
- The manual checker should return the repaired `payload_yaml` when a repair was applied so the editor can reflect the recovered draft.
- The default server-proof provider is ChatGPT using the logged-in session `extai-chatgpt-spot`.

## Output Contract

- State which saved artifact folder was rechecked, if any.
- State whether the saved-corpus recheck recovered the target samples.
- State the live restarted-server artifact folder.
- State the fresh sample count and whether the HTTP checker path was used.
- Call out whether the result proves only the parser repair, or both parser repair and live server behavior.
