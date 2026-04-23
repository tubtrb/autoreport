# Manual AI Regression Batch Run And Logging

## Canonical Entry Point

Use the suite wrapper for diagnostics and spot checks:

```powershell
powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http
```

Use the dedicated release-gate wrapper for the official low-trigger ChatGPT web
signoff path:

```powershell
powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http
```

`run_manual_ai_regression.ps1` remains the flexible suite runner for
diagnostics, spot checks, and corpus-style investigation. The official release
gate is the paced single-session 20-chat runbook behind
`run_manual_ai_release_gate.ps1`.

The ChatGPT transport is attach-only. `tests/verif_test` must not launch,
close, or restart Chrome. `-Session` remains part of the CLI surface, but it is
treated as the canonical profile key for the user-opened Chrome session that
the runner attaches to.

## Canonical Profile Contract

Canonical profile key:

- `extai-chatgpt-spot`

Canonical persistent profile path:

- `.codex\playwright\profiles\extai-chatgpt-spot`

Remembered last-success URL:

- `.codex\playwright\extai-chatgpt-spot-last-url.txt`

Legacy one-time recovery source:

- `output\playwright\chrome-userdata-copy`

Do not use `profile_default\extai-chatgpt-spot-bootstrap2` as the canonical
ChatGPT regression profile. It only carries challenge-era state and is not the
historical regression conversation base.

If the canonical `.codex` profile does not exist yet, copy the legacy recovery
source into `.codex\playwright\profiles\extai-chatgpt-spot` once, then reuse
only the `.codex` profile going forward.

Whale or other non-canonical browser windows are out of scope. The runner only
trusts the manually opened regular Chrome session that uses the canonical
profile plus the attach port.

## Attach Contract

The user must open Chrome manually from the terminal with the canonical profile
and a fixed attach port:

- `--remote-debugging-port=9222`
- `--user-data-dir=.codex/playwright/profiles/extai-chatgpt-spot`
- one real `https://chatgpt.com/` conversation page open

The runner then attaches with Playwright CDP and inspects the existing browser
state. It does not create the browser process itself, and it does not close or
kill profile-holding Chrome processes.

After attach, the runner still inspects Windows process command lines. If
`--no-sandbox` is present on the attached browser tree, the session fails
immediately and diagnostics record `no_sandbox_detected=true`.

## Session Check Only

Use validate-only mode after manual profile seeding and before any smoke or
release-gate run:

```powershell
powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
powershell -File .\run_manual_ai_release_gate.ps1 -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
```

This mode now performs attach plus readiness validation. The command skips
preflight, HTTP health, and case execution, but it still writes the same root
summary plus dedicated session diagnostics.

When the canonical profile is cold or recently challenge-blocked, open it first
in a user-launched regular Chrome session from the terminal:

```powershell
$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
  $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}
$profile = Join-Path (Get-Location) ".codex\playwright\profiles\extai-chatgpt-spot"
& $chrome --remote-debugging-port=9222 --user-data-dir="$profile" "https://chatgpt.com/"
```

In that regular Chrome session, complete login or Cloudflare approval, open one
real ChatGPT conversation, optionally send one short message, and keep Chrome
open. Only after that should you rerun `-SessionCheckOnly`.

The shared implementation lives under:

- [`tests/verif_test/pipeline.py`](../../../tests/verif_test/pipeline.py)
- [`tests/verif_test/chatgpt.py`](../../../tests/verif_test/chatgpt.py)
- [`tests/verif_test/release_gate.py`](../../../tests/verif_test/release_gate.py)

## Readiness And Page Selection

The runner inspects only the pages that are already open in the attached manual
Chrome session.

Readiness is determined across all pages in the persistent context. Candidate
selection is fixed to the following priority:

1. `https://chatgpt.com/c/*` with a composer or new-chat button
2. `https://chatgpt.com/*` with a composer or new-chat button
3. the remembered last-success URL
4. any other `chatgpt.com` page

The session is not considered ready from DOM state alone. The runner also
watches recent responses for challenge or auth failures on:

- `/cdn-cgi/challenge-platform/*`
- `/backend-api/sentinel/*`
- `/backend-api/f/conversation/prepare`
- `/backend-api/sentinel/chat-requirements/prepare`
- `/api/auth/session`
- `/backend-api/me`

If those responses show a challenge or login loop, readiness resolves to
`challenge_blocked` or `login_required` even when the page appears interactive.

## Retry And Recovery Policy

`run_manual_ai_regression.ps1` keeps the more aggressive but finite diagnostic
policy:

- session attach check: at most 3 attach attempts
- per-case ChatGPT transport: at most 3 attempts on the already-open manual
  browser session
- checker and generate: retry only for network exceptions or HTTP 5xx, up to 2
  extra attempts after the first call

Semantic 4xx failures, validation failures, and extraction failures are not
retried. Case failure does not stop the suite.

`run_manual_ai_release_gate.ps1` uses a separate low-trigger policy:

- one attach/readiness check only after the manual profile seed
- one ChatGPT transport attempt per case
- no browser relaunch during the 20-chat gate
- if challenge/login/auth transport signals appear, stop the remaining chunks
  immediately
- checker and generate still retry only for network exceptions or HTTP 5xx

## Fixed Execution Order

1. run narrow preflight tests
2. expand the suite into concrete cases
3. write `starter.yaml`, `prompt.txt`, and `case-manifest.json`
4. attach to and validate the manually opened ChatGPT session
5. send each prompt to ChatGPT
6. extract `report_content` YAML
7. call `/api/manual-draft-check`
8. call `/api/generate` for checker-pass cases
9. inspect the generated PPTX
10. write summary and review queue artifacts

The official low-trigger release gate uses one fixed 20-chat runbook in one
browser session:

1. manual open in regular Chrome with the canonical profile and attach port
2. `-SessionCheckOnly`
3. Chunk A: `smoke` 3 chats
4. cooldown 5 minutes
5. Chunk B: `regression` 5 chats
6. cooldown 10 minutes
7. Chunk C: `full` 6 chats
8. cooldown 15 minutes
9. Chunk D repeat set:
   - `01_one_image_canary`
   - `05_balanced_canary`
   - `10_full_family_canary`
   - `05_dense_text_canary`
   - `01_two_image_canary`
   - `01_three_image_canary`

Inside each chunk, the runner idles 45 seconds after every completed case and
adds another 3 minutes after every 3 completed chats.

## Output Layout

Standard output root:

- `output/verif_test/<run-id>/`

Run root files:

- `run-config.json`
- `events.jsonl`
- `session-check.json`
- `session-check.md`
- `session-page.txt`
- `session-network.jsonl`
- `session-console.jsonl`
- `session-screenshot.png`
- `summary.json`
- `summary.csv`
- `summary.md`
- `review-queue.json`
- `review-queue.md`

Release-gate root files also include:

- `chunk-results.json`
- `chunk-results.md`

Compatibility root files also remain available:

- `run-metadata.json`
- `summary.txt`

Per-case files:

- `starter.yaml`
- `prompt.txt`
- `case-manifest.json`
- `ai-raw.txt`
- `yaml-candidate.yaml`
- `checker.json`
- `generate.json`
- `pptx-inspection.json`
- `artifact.pptx`
- `events.jsonl`
- `transport-state.json`
- `transport-network.jsonl`
- `transport-console.jsonl`

Compatibility per-case files also remain available:

- `raw-turn.txt`

## Event Schema

Each JSONL event uses:

- `ts`
- `run_id`
- `case_id`
- `stage`
- `status`
- `duration_ms`
- `failure_class`
- `message`
- `artifact`

## Summary Fields

`summary.json`, `summary.md`, and `summary.csv` now surface the transport
attempt and launcher diagnostics needed to explain recovery behavior:

- `transport_attempts`
- `session_relaunches`
- `no_sandbox_detected`
- `selected_page_url`
- `selected_page_title`
- `recent_response_failures`

The release gate also adds:

- `runbook`
- `planned_chat_count`
- `completed_chat_count`
- `chunk_results`
- `cooldown_schedule_applied`
- `guard_trip_reason`
- `guard_trip_stage`
- `single_session_browser_relaunches`

For the release gate, `single_session_browser_relaunches` should stay `0`
through the whole run. Any non-zero value is a policy regression.

## Diagnostic Batch Loops

Prompt-pack batch tools such as
`codex\skills\ai-corpus-verification\scripts\run_chatgpt_batch_matrix.ps1` are
diagnostic or stress tools only. They are not the release-gate operator path.

## Hard Failure Taxonomy

- `ai_transport_failure`
- `yaml_extract_failure`
- `checker_failure`
- `generate_failure`
- `pptx_inspection_failure`

These classes are the only blocking per-case failure buckets in v1.

## Session Check Reasons

- `not_open`
- `in_memory_profile`
- `wrong_profile`
- `challenge_blocked`
- `login_required`
- `wrong_page`
- `ready`

The session-check payload records at least:

- `launcher`
- `browser_pid`
- `no_sandbox_detected`
- `expected_profile_dir`
- `actual_profile_dir`
- `tabs`
- `page_url`
- `page_title`
- `selected_page_url`
- `selected_page_title`
- `has_composer`
- `has_new_chat_button`
- `page_candidates`
- `recent_response_failures`
