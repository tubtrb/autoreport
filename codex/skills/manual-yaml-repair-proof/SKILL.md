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
- Read `../../../docs/architecture/verif_test/03_ai_batch_run_logging.md`.
- Read `../../../docs/architecture/verif_test/04_result_review_gate.md`.
- Read `../../../autoreport/web/app.py` when the parser, checker, starter prompt, or manual flow changed.
- Read `../../../tests/test_web_app.py` and `../../../tests/test_web_serve.py` before claiming the proof is complete.
- Read `references/proof-flow.md`.
- Use `scripts/recheck_manual_corpus.py` to replay saved corpus artifacts through the current in-process repair and checker path.
- Use `..\..\..\run_manual_ai_regression.ps1` as the canonical fresh smoke runner for the public-manual HTTP path.
- Treat `scripts/run_server_proof.ps1` as a convenience wrapper when the task specifically wants the older proof bundle flow.
- Canonical ChatGPT session key: `extai-chatgpt-spot`.
- Canonical persistent profile path: `.codex\playwright\profiles\extai-chatgpt-spot`.
- Remembered last-success URL path: `.codex\playwright\extai-chatgpt-spot-last-url.txt`.
- Legacy one-time recovery source: `output\playwright\chrome-userdata-copy`.

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
- If the ChatGPT profile is cold or challenge/login is expected, first tell the
  user to seed the canonical profile manually from a regular terminal-launched
  Chrome session:

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
  open before the runner starts.
- Validate the manually opened browser session after that manual seed step:
  `powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http -SessionCheckOnly`
- Run at least one fresh ChatGPT suite smoke against the HTTP checker path:
  `powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http`
- Do not let the runner launch or relaunch the canonical profile itself. It may
  only attach to the manually opened Chrome session. Do not pre-open an
  attach-only `playwright-cli` session.
- When the claim is broader than a local smoke, use `scripts/run_server_proof.ps1 -CorpusCount <n>` or the prompt-pack collector wrapper for a larger corpus run.

4. Keep the proof route production-faithful.
- Use the full manual comments exported from `autoreport/web/app.py`, not synthetic strict/medium/loose/adversarial packs, unless the user explicitly asks for stress testing.
- Prefer `--checker-mode http` for the restarted-server proof so the live route is exercised end to end.
- Use in-process recheck only for saved-corpus salvage measurement.

5. Separate the two proof questions.
- "Does the code know how to repair this class of YAML drift?" -> saved corpus recheck.
- "Does the restarted server actually do it on the live path?" -> fresh HTTP smoke or corpus run.
- Do not let one substitute for the other when both are relevant.

## Current Repo Defaults

- The common recovery target is manual `report_content` YAML drift from external AI replies, especially fenced/prose-wrapped/rootless drafts plus indentation collapse.
- The auto-repair path is expected to run before parse in the manual checker, compile, and generate entrypoints.
- The manual checker should return the repaired `payload_yaml` when a repair was applied so the editor can reflect the recovered draft.
- The default server-proof provider is ChatGPT using the canonical profile key `extai-chatgpt-spot`.
- The canonical proof path only trusts the manually opened Chrome session that
  uses the canonical profile plus the attach port. Do not treat Whale or
  another regular browser window as equivalent proof state.
- `-SessionCheckOnly` now means attach plus readiness validation, not browser
  relaunch. It is a readiness verifier that should run after the user has
  manually opened the canonical profile in regular Chrome when login or
  Cloudflare approval is needed.
- Canonical proof artifacts now live under `output/verif_test/<run-id>/`.

## Output Contract

- State which saved artifact folder was rechecked, if any.
- State whether the saved-corpus recheck recovered the target samples.
- State the live restarted-server artifact folder.
- State the fresh sample count and whether the HTTP checker path was used.
- Call out whether the result proves only the parser repair, or both parser repair and live server behavior.
