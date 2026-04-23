# Manual AI Regression Result Gate

## Run Status Rules

- `FAIL`: any hard failure exists, or a representative visual review is
  explicitly marked `fail`
- `REVIEW`: no hard failures exist, but a fixed representative visual review is
  still pending
- `PASS`: no hard failures exist and all required representative reviews are
  recorded as `pass`

## Fixed Review Scope

Representative review stays deterministic. Do not use dynamic heuristics.

- `01_one_image_canary`
- `05_balanced_canary` for `regression` and `full`
- `10_full_family_canary` for `full`

Record the review result with:

```powershell
.\venv\Scripts\python.exe tests\verif_test\record_visual_review.py --run-dir output\verif_test\<run-folder> --case-id 01_one_image_canary --decision pass --note "visual ok"
```

For `release-gate`, keep the same representative review set:

- `01_one_image_canary`
- `05_balanced_canary`
- `10_full_family_canary`

The repeated tail chunk does not add extra visual-review obligations for the
same case IDs.

## Why Human Review Still Exists

The script can prove:

- the attach-only ChatGPT transport found a usable page in the manually opened
  Chrome session or failed with recorded transport diagnostics
- YAML was extracted
- the checker passed
- PPTX generation completed
- the PPTX can be opened and structurally inspected

The script cannot yet prove visual quality issues such as:

- clipped text
- misleading image placement
- awkward title/body balance
- technically valid but visually wrong output

The representative review step exists to calibrate those visual risks without
forcing a person to open every artifact.

## Transport-Aware Result Reading

The run summary now exposes transport recovery state instead of only a final
transport pass/fail bit. Use these fields when deciding whether a run failed on
the browser session itself or on a later case step:

- `transport_attempts`
- `session_relaunches`
- `no_sandbox_detected`
- `selected_page_url`
- `recent_response_failures`

The low-trigger release gate adds root-level runbook state so the operator can
see exactly where the single-session run stopped:

- `runbook`
- `planned_chat_count`
- `completed_chat_count`
- `chunk_results`
- `cooldown_schedule_applied`
- `guard_trip_reason`
- `guard_trip_stage`
- `single_session_browser_relaunches`

Read `chunk-results.json` or `chunk-results.md` first when the gate stops
mid-run. They show whether the session ended in Chunk A/B/C/D and whether later
chunks were blocked by a transport guard trip.

For the release gate, `single_session_browser_relaunches` must remain `0`
through the whole run. If a challenge or auth guard trips during the run, the
expected result is a clear `FAIL` plus a stopped run, not more relaunches.

After the attach-only transport retries are exhausted, `stop_step` should point
to the actual blocking case step. A ready manual session should no longer fail
only because the current tab happened to be a stale `please wait` challenge
page.

## Active Unittest Map

Use these as the narrow floor before broadening:

- public manual prompt/check/generate surface:
  - `tests.test_web_app`
  - `tests.test_web_serve`
- debug/manual mutation surface:
  - `tests.test_web_debug_app`
- PPTX landing or generation core:
  - `tests.test_autofill`
  - `tests.test_generator`
  - `tests.test_pptx_writer`
- verification framework itself:
  - `tests.test_verif_test`

## Canonical References

- [`tests/verif_test/pipeline.py`](../../../tests/verif_test/pipeline.py)
- [`tests/verif_test/release_gate.py`](../../../tests/verif_test/release_gate.py)
- [`tests/verif_test/record_visual_review.py`](../../../tests/verif_test/record_visual_review.py)
