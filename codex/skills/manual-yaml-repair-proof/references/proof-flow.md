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
powershell -File codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 -Session extai-chatgpt-spot -SmokeCount 1
```

## Stronger Sequence

```powershell
powershell -File codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 -Session extai-chatgpt-spot -SmokeCount 1 -CorpusCount 20
```

Use the stronger sequence when the user wants a fresh live corpus result rather
than only a smoke check.
