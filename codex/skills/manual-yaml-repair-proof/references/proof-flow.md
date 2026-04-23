# Manual YAML Repair Proof Flow

Use this reference when a change claims that Autoreport now recovers common
manual YAML drift from external AI output.

## Proof Levels

1. Code proof
- Narrow tests for the public manual flow pass.

2. Saved-corpus salvage proof
- A previously captured real-provider artifact folder is replayed through the
  current repair plus checker path.
- This proves that the new logic actually recovers the historical failures.

3. Live restarted-server proof
- The local server is up on `/healthz`.
- A fresh ChatGPT conversation uses the full product prompt comments.
- The HTTP checker route is hit, not just the in-process checker.

## Minimum Recommended Sequence

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_web_app tests.test_web_serve
.\venv\Scripts\python.exe codex\skills\manual-yaml-repair-proof\scripts\recheck_manual_corpus.py --artifact-dir output\playwright\<existing-folder>
$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
  $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}
$profile = Join-Path (Get-Location) ".codex\playwright\profiles\extai-chatgpt-spot"
& $chrome --remote-debugging-port=9222 --user-data-dir="$profile" "https://chatgpt.com/"
# login/challenge in that regular Chrome session, open one real conversation,
# optionally send one short message, then keep Chrome open for the attach-only runner
powershell -File .\run_manual_ai_regression.ps1 -Suite smoke -Session extai-chatgpt-spot -Mode http -SessionCheckOnly
powershell -File codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 -Session extai-chatgpt-spot -SmokeCount 1
```

## Stronger Sequence

```powershell
powershell -File codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 -Session extai-chatgpt-spot -SmokeCount 1 -CorpusCount 20
```

Use the stronger sequence when the user wants a fresh live corpus result rather
than only a smoke check.

The ChatGPT browser is now user-opened. The smoke and proof commands attach to
that already-open Chrome session and validate readiness before they start
sending prompts. Do not use an AI-opened browser as the login or
challenge-approval path. Open the canonical profile first in a user-launched
regular Chrome session from the terminal with `--remote-debugging-port=9222`,
then keep that browser open while running `-SessionCheckOnly` and the proof
commands.

Use `output\playwright\chrome-userdata-copy` only as the one-time legacy source
when restoring `.codex\playwright\profiles\extai-chatgpt-spot`.
