from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import Any, Callable

from tests.verif_test.catalog import (
    PreparedSample,
    REVIEW_CASE_IDS,
    build_prepared_sample,
    load_case_catalog,
    validate_yaml_candidate_against_manifest,
)
from tests.verif_test.chatgpt import (
    capture_chatgpt_transport_diagnostics,
    canonical_profile_dir,
    collect_chatgpt_response_once,
    export_chatgpt_transport_artifacts,
    inspect_chatgpt_session,
    normalize_yaml_candidate,
)
from tests.verif_test.pipeline import (
    DEFAULT_BASE_URL,
    DEFAULT_PREFLIGHT_MODULES,
    _append_case_event,
    _append_event,
    _apply_transport_metrics,
    _build_case_step_statuses,
    _build_run_id,
    _duration_ms,
    _mark_case_step_status,
    _overall_message,
    _report_progress,
    _run_checker_with_retry,
    _run_generate_with_retry,
    _timestamp,
    _write_json,
    _write_text,
    build_summary_payload,
    check_health,
    inspect_pptx_artifact,
    is_yaml_extract_failure,
    run_preflight_tests,
    write_summary_artifacts,
)


RELEASE_GATE_RUNBOOK = "chatgpt-web-low-trigger-release-gate-v1"
INTER_CASE_IDLE_SECONDS = 45.0
TRIPLE_CASE_IDLE_SECONDS = 180.0


@dataclass(frozen=True)
class ReleaseGateChunk:
    index: int
    name: str
    label: str
    case_ids: tuple[str, ...]
    cooldown_after_seconds: int


@dataclass(frozen=True)
class ReleaseGateTransportBudget:
    send_wait_seconds: float
    poll_seconds: float
    max_polls: int


def build_release_gate_plan() -> tuple[ReleaseGateChunk, ...]:
    return (
        ReleaseGateChunk(
            index=1,
            name="chunk_a_smoke",
            label="Chunk A: smoke",
            case_ids=(
                "01_one_image_canary",
                "01_two_image_canary",
                "01_three_image_canary",
            ),
            cooldown_after_seconds=300,
        ),
        ReleaseGateChunk(
            index=2,
            name="chunk_b_regression",
            label="Chunk B: regression",
            case_ids=(
                "01_one_image_canary",
                "01_two_image_canary",
                "01_three_image_canary",
                "05_balanced_canary",
                "05_dense_text_canary",
            ),
            cooldown_after_seconds=600,
        ),
        ReleaseGateChunk(
            index=3,
            name="chunk_c_full",
            label="Chunk C: full",
            case_ids=(
                "01_one_image_canary",
                "01_two_image_canary",
                "01_three_image_canary",
                "05_balanced_canary",
                "05_dense_text_canary",
                "10_full_family_canary",
            ),
            cooldown_after_seconds=900,
        ),
        ReleaseGateChunk(
            index=4,
            name="chunk_d_repeat",
            label="Chunk D: repeat set",
            case_ids=(
                "01_one_image_canary",
                "05_balanced_canary",
                "10_full_family_canary",
                "05_dense_text_canary",
                "01_two_image_canary",
                "01_three_image_canary",
            ),
            cooldown_after_seconds=0,
        ),
    )


def prepare_release_gate_samples() -> tuple[PreparedSample, ...]:
    catalog = load_case_catalog()
    review_seen: set[str] = set()
    prepared: list[PreparedSample] = []
    chat_index = 0
    for chunk in build_release_gate_plan():
        for case_id in chunk.case_ids:
            chat_index += 1
            base_sample = build_prepared_sample(catalog[case_id])
            review_required = bool(
                case_id in REVIEW_CASE_IDS
                and base_sample.expected_review_required
                and case_id not in review_seen
            )
            if review_required:
                review_seen.add(case_id)
            manifest = {
                **base_sample.manifest,
                "runbook": RELEASE_GATE_RUNBOOK,
                "chunk_index": chunk.index,
                "chunk_name": chunk.name,
                "chunk_label": chunk.label,
                "chat_index": chat_index,
                "cooldown_after_seconds": chunk.cooldown_after_seconds,
            }
            prepared.append(
                PreparedSample(
                    prompt_id=f"release-gate-{chat_index:02d}-{case_id}",
                    case_id=base_sample.case_id,
                    label=base_sample.label,
                    prompt=base_sample.prompt,
                    starter_yaml=base_sample.starter_yaml,
                    image_ref_count=base_sample.image_ref_count,
                    expected_review_required=review_required,
                    manifest=manifest,
                )
            )
    return tuple(prepared)


def _transport_budget_for_sample(
    sample: PreparedSample,
    *,
    send_wait_seconds: float,
    poll_seconds: float,
    max_polls: int,
) -> ReleaseGateTransportBudget:
    tuned_max_polls = int(max_polls)
    text_density = str(sample.manifest.get("text_density", "") or "").lower()
    image_ref_count = int(sample.manifest.get("image_ref_count", 0) or 0)

    if image_ref_count >= 3:
        tuned_max_polls = max(tuned_max_polls, 28)
    if text_density == "balanced":
        tuned_max_polls = max(tuned_max_polls, 32)
    elif text_density == "dense":
        tuned_max_polls = max(tuned_max_polls, 36)

    return ReleaseGateTransportBudget(
        send_wait_seconds=float(send_wait_seconds),
        poll_seconds=float(poll_seconds),
        max_polls=tuned_max_polls,
    )


def execute_release_gate_run(
    *,
    session: str,
    mode: str,
    output_root: Path,
    base_url: str = DEFAULT_BASE_URL,
    run_dir: Path | None = None,
    transport: Callable[[PreparedSample], str] | None = None,
    run_preflight: bool = True,
    send_wait_seconds: float = 0.8,
    poll_seconds: float = 3.0,
    max_polls: int = 20,
    python_executable: Path | None = None,
    session_check_only: bool = False,
    progress: Callable[[str], None] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> Path:
    if mode not in {"http", "local"}:
        raise RuntimeError("mode must be one of: http, local")

    resolved_python = python_executable or Path(sys.executable)
    started_at = _timestamp()
    resolved_output_root = output_root.resolve()
    resolved_run_dir = run_dir.resolve() if run_dir is not None else (
        resolved_output_root / _build_run_id("release-gate")
    )
    resolved_run_dir.mkdir(parents=True, exist_ok=True)
    root_events_path = resolved_run_dir / "events.jsonl"
    planned_chunks = _initial_chunk_results()
    cooldown_schedule: list[dict[str, Any]] = []
    samples = prepare_release_gate_samples()
    run_config = {
        "run_id": resolved_run_dir.name,
        "suite": "release-gate",
        "mode": mode,
        "session": session,
        "base_url": base_url,
        "session_check_only": session_check_only,
        "expected_profile_dir": str(canonical_profile_dir(session)),
        "sample_count": len(samples),
        "started_at": started_at,
        "prompt_pack_path": None,
        "preflight_modules": list(DEFAULT_PREFLIGHT_MODULES),
        "review_case_ids": list(sorted(REVIEW_CASE_IDS)),
        "runbook": RELEASE_GATE_RUNBOOK,
        "cases": [sample.manifest for sample in samples],
    }
    _write_json(resolved_run_dir / "run-config.json", run_config)
    _write_json(resolved_run_dir / "run-metadata.json", run_config)
    _append_event(
        root_events_path,
        run_id=resolved_run_dir.name,
        case_id="_run",
        stage="run",
        status="started",
        duration_ms=0.0,
        message=f"Starting {RELEASE_GATE_RUNBOOK} with {len(samples)} planned chats.",
    )
    _report_progress(
        progress,
        f"[release-gate] starting runbook={RELEASE_GATE_RUNBOOK} mode={mode} chats={len(samples)} run_dir={resolved_run_dir}",
    )

    preflight_result = _run_preflight_if_needed(
        run_preflight=run_preflight,
        session_check_only=session_check_only,
        resolved_python=resolved_python,
        resolved_run_dir=resolved_run_dir,
        root_events_path=root_events_path,
        progress=progress,
    )
    if preflight_result is not None and not preflight_result["ok"]:
        summary = _build_release_gate_summary(
            run_config=run_config,
            cases=[],
            preflight=preflight_result,
            health=None,
            session_check=None,
            started_at=started_at,
            finished_at=_timestamp(),
            chunk_results=_block_chunk_results(planned_chunks, reason="preflight_failed"),
            cooldown_schedule=cooldown_schedule,
            completed_chat_count=0,
            guard_trip_reason="",
            guard_trip_stage="",
            single_session_browser_relaunches=0,
        )
        write_summary_artifacts(resolved_run_dir, summary)
        _write_chunk_artifacts(resolved_run_dir, summary["chunk_results"])
        return resolved_run_dir

    health_result = _run_health_check_if_needed(
        mode=mode,
        session_check_only=session_check_only,
        base_url=base_url,
        root_events_path=root_events_path,
        run_id=resolved_run_dir.name,
        progress=progress,
    )
    if health_result is not None and not health_result["ok"]:
        summary = _build_release_gate_summary(
            run_config=run_config,
            cases=[],
            preflight=preflight_result,
            health=health_result,
            session_check=None,
            started_at=started_at,
            finished_at=_timestamp(),
            chunk_results=_block_chunk_results(planned_chunks, reason="healthz_failed"),
            cooldown_schedule=cooldown_schedule,
            completed_chat_count=0,
            guard_trip_reason="",
            guard_trip_stage="",
            single_session_browser_relaunches=0,
        )
        write_summary_artifacts(resolved_run_dir, summary)
        _write_chunk_artifacts(resolved_run_dir, summary["chunk_results"])
        return resolved_run_dir

    _report_progress(progress, f"[release-gate] checking seeded ChatGPT session: {session}")
    session_check = inspect_chatgpt_session(
        session=session,
        artifact_dir=resolved_run_dir,
        allow_manual_recovery=False,
        bootstrap_attempts=1,
        progress=progress,
    )
    _append_event(
        root_events_path,
        run_id=resolved_run_dir.name,
        case_id="_run",
        stage="chatgpt_session",
        status="success" if session_check["ok"] else "failure",
        duration_ms=0.0,
        failure_class="ai_transport_failure" if not session_check["ok"] else None,
        message=session_check["message"],
    )
    if session_check_only:
        summary = _build_release_gate_summary(
            run_config=run_config,
            cases=[],
            preflight=None,
            health=None,
            session_check=session_check,
            started_at=started_at,
            finished_at=_timestamp(),
            chunk_results=_block_chunk_results(
                planned_chunks,
                reason="session_check_only",
                blocked_status="PENDING",
            ),
            cooldown_schedule=cooldown_schedule,
            completed_chat_count=0,
            guard_trip_reason=session_check["message"] if not session_check["ok"] else "",
            guard_trip_stage="chatgpt_session" if not session_check["ok"] else "",
            single_session_browser_relaunches=0,
        )
        write_summary_artifacts(resolved_run_dir, summary)
        _write_chunk_artifacts(resolved_run_dir, summary["chunk_results"])
        return resolved_run_dir
    if not session_check["ok"]:
        summary = _build_release_gate_summary(
            run_config=run_config,
            cases=[],
            preflight=preflight_result,
            health=health_result,
            session_check=session_check,
            started_at=started_at,
            finished_at=_timestamp(),
            chunk_results=_block_chunk_results(planned_chunks, reason=session_check["reason"]),
            cooldown_schedule=cooldown_schedule,
            completed_chat_count=0,
            guard_trip_reason=session_check["message"],
            guard_trip_stage="chatgpt_session",
            single_session_browser_relaunches=0,
        )
        write_summary_artifacts(resolved_run_dir, summary)
        _write_chunk_artifacts(resolved_run_dir, summary["chunk_results"])
        return resolved_run_dir

    case_rows: list[dict[str, Any]] = []
    completed_chat_count = 0
    guard_trip_reason = ""
    guard_trip_stage = ""
    single_session_browser_relaunches = 0
    if transport is None:
        def transport_fn(sample: PreparedSample) -> str:
            budget = _transport_budget_for_sample(
                sample,
                send_wait_seconds=send_wait_seconds,
                poll_seconds=poll_seconds,
                max_polls=max_polls,
            )
            return collect_chatgpt_response_once(
                session=session,
                prompt=sample.prompt,
                expected_manifest=sample.manifest,
                send_wait_seconds=budget.send_wait_seconds,
                poll_seconds=budget.poll_seconds,
                max_polls=budget.max_polls,
            )
    else:
        transport_fn = transport
    chunks_by_name = {chunk["name"]: chunk for chunk in planned_chunks}
    total_samples = len(samples)
    sleep_impl = sleep_fn or time.sleep

    for index, sample in enumerate(samples, start=1):
        aborted = _execute_release_gate_case(
            index=index,
            total_samples=total_samples,
            sample=sample,
            session=session,
            mode=mode,
            base_url=base_url,
            root_events_path=root_events_path,
            run_dir=resolved_run_dir,
            transport=transport,
            transport_fn=transport_fn,
            progress=progress,
            sleep_impl=sleep_impl,
            cooldown_schedule=cooldown_schedule,
            case_rows=case_rows,
            chunks_by_name=chunks_by_name,
            state={
                "completed_chat_count": completed_chat_count,
                "guard_trip_reason": guard_trip_reason,
                "guard_trip_stage": guard_trip_stage,
                "single_session_browser_relaunches": single_session_browser_relaunches,
            },
        )
        completed_chat_count = int(aborted["completed_chat_count"])
        guard_trip_reason = str(aborted["guard_trip_reason"])
        guard_trip_stage = str(aborted["guard_trip_stage"])
        single_session_browser_relaunches = int(aborted["single_session_browser_relaunches"])
        if guard_trip_reason:
            _block_chunk_results(
                planned_chunks,
                reason=guard_trip_reason,
                from_chunk_index=int(sample.manifest["chunk_index"]) + 1,
            )
            break

    for chunk_result in planned_chunks:
        if chunk_result["status"] == "RUNNING":
            chunk_result["status"] = "PASS"
            chunk_result["finished_at"] = _timestamp()

    summary = _build_release_gate_summary(
        run_config=run_config,
        cases=case_rows,
        preflight=preflight_result,
        health=health_result,
        session_check=session_check,
        started_at=started_at,
        finished_at=_timestamp(),
        chunk_results=planned_chunks,
        cooldown_schedule=cooldown_schedule,
        completed_chat_count=completed_chat_count,
        guard_trip_reason=guard_trip_reason,
        guard_trip_stage=guard_trip_stage,
        single_session_browser_relaunches=single_session_browser_relaunches,
    )
    write_summary_artifacts(resolved_run_dir, summary)
    _write_chunk_artifacts(resolved_run_dir, summary["chunk_results"])
    _append_event(
        root_events_path,
        run_id=resolved_run_dir.name,
        case_id="_run",
        stage="run",
        status="success" if summary["overall_status"] != "FAIL" else "failure",
        duration_ms=0.0,
        message=f"Run completed with status {summary['overall_status']}.",
    )
    _report_progress(progress, f"[release-gate] completed with {summary['overall_status']}: {resolved_run_dir}")
    return resolved_run_dir


def _run_preflight_if_needed(
    *,
    run_preflight: bool,
    session_check_only: bool,
    resolved_python: Path,
    resolved_run_dir: Path,
    root_events_path: Path,
    progress: Callable[[str], None] | None,
) -> dict[str, Any] | None:
    if not run_preflight or session_check_only:
        return None
    _report_progress(
        progress,
        "[release-gate] running preflight: python -m unittest tests.test_web_app tests.test_web_serve",
    )
    result = run_preflight_tests(
        python_executable=resolved_python,
        run_dir=resolved_run_dir,
        modules=DEFAULT_PREFLIGHT_MODULES,
    )
    _append_event(
        root_events_path,
        run_id=resolved_run_dir.name,
        case_id="_run",
        stage="preflight",
        status="success" if result["ok"] else "failure",
        duration_ms=0.0,
        failure_class="preflight_failure" if not result["ok"] else None,
        message=result["message"],
        artifact=str((resolved_run_dir / "preflight.stdout.log").relative_to(resolved_run_dir)),
    )
    return result


def _run_health_check_if_needed(
    *,
    mode: str,
    session_check_only: bool,
    base_url: str,
    root_events_path: Path,
    run_id: str,
    progress: Callable[[str], None] | None,
) -> dict[str, Any] | None:
    if mode != "http" or session_check_only:
        return None
    _report_progress(progress, f"[release-gate] checking local app health: {base_url.rstrip('/')}/healthz")
    result = check_health(base_url)
    _append_event(
        root_events_path,
        run_id=run_id,
        case_id="_run",
        stage="healthz",
        status="success" if result["ok"] else "failure",
        duration_ms=0.0,
        failure_class="ai_transport_failure" if not result["ok"] else None,
        message=result["message"],
    )
    return result


def _execute_release_gate_case(
    *,
    index: int,
    total_samples: int,
    sample: PreparedSample,
    session: str,
    mode: str,
    base_url: str,
    root_events_path: Path,
    run_dir: Path,
    transport: Callable[[PreparedSample], str] | None,
    transport_fn: Callable[[PreparedSample], str],
    progress: Callable[[str], None] | None,
    sleep_impl: Callable[[float], None],
    cooldown_schedule: list[dict[str, Any]],
    case_rows: list[dict[str, Any]],
    chunks_by_name: dict[str, dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    chunk_name = str(sample.manifest["chunk_name"])
    chunk_result = chunks_by_name[chunk_name]
    if chunk_result["status"] == "PENDING":
        chunk_result["status"] = "RUNNING"
        chunk_result["started_at"] = _timestamp()
    case_dir = run_dir / f"{index:03d}-{sample.case_id}"
    case_dir.mkdir(parents=True, exist_ok=True)
    case_events_path = case_dir / "events.jsonl"
    _write_text(case_dir / "starter.yaml", sample.starter_yaml)
    _write_text(case_dir / "prompt.txt", sample.prompt)
    _write_json(case_dir / "case-manifest.json", sample.manifest)
    _report_progress(
        progress,
        f"[release-gate] case {index}/{total_samples} {sample.case_id}: chunk={chunk_name}",
    )
    row: dict[str, Any] = {
        "index": index,
        "chunk_index": int(sample.manifest["chunk_index"]),
        "chunk_name": chunk_name,
        "chunk_label": str(sample.manifest["chunk_label"]),
        "chat_index": int(sample.manifest["chat_index"]),
        "sample_id": case_dir.name,
        "case_id": sample.case_id,
        "prompt_id": sample.prompt_id,
        "label": sample.label,
        "case_dir": str(case_dir),
        "review_required": bool(sample.expected_review_required),
        "review_decision": None,
        "status": "success",
        "failure_class": None,
        "checker_ok": False,
        "checker_message": "",
        "blocking_issue_count": 0,
        "warning_count": 0,
        "generate_ok": False,
        "pptx_openable": False,
        "slide_count": 0,
        "shape_count": 0,
        "image_count": 0,
        "artifact_pptx": None,
        "last_completed_step": None,
        "stop_step": None,
        "transport_attempts": 0,
        "session_relaunches": 0,
        "no_sandbox_detected": False,
        "selected_page_url": "",
        "selected_page_title": "",
        "recent_response_failures": [],
        "step_statuses": _build_case_step_statuses(),
    }
    _mark_case_step_status(row, "prompt_artifacts", "success")
    _append_case_event(
        root_events_path,
        case_events_path,
        run_id=run_dir.name,
        case_id=sample.case_id,
        stage="prompt_artifacts",
        status="success",
        duration_ms=0.0,
        message="Wrote starter.yaml, prompt.txt, and case-manifest.json.",
        artifact=str((case_dir / "case-manifest.json").relative_to(run_dir)),
    )
    try:
        raw_turn_text = transport_fn(sample)
        _write_text(case_dir / "ai-raw.txt", raw_turn_text)
        _write_text(case_dir / "raw-turn.txt", raw_turn_text)
        if transport is None:
            transport_state = capture_chatgpt_transport_diagnostics(session)
            _write_json(case_dir / "transport-state.json", transport_state)
            export_chatgpt_transport_artifacts(session, case_dir)
            _apply_transport_metrics(row, transport_state)
        _mark_case_step_status(row, "ai_transport", "success")
        _append_case_event(
            root_events_path,
            case_events_path,
            run_id=run_dir.name,
            case_id=sample.case_id,
            stage="ai_transport",
            status="success",
            duration_ms=0.0,
            message="Received ChatGPT response.",
            artifact=str((case_dir / "ai-raw.txt").relative_to(run_dir)),
        )
        state["completed_chat_count"] = int(state["completed_chat_count"]) + 1
        chunk_result["completed_chat_count"] += 1
        state["single_session_browser_relaunches"] = max(
            int(state["single_session_browser_relaunches"]),
            int(row.get("session_relaunches", 0)),
        )
    except Exception as exc:
        row["status"] = "failure"
        row["failure_class"] = "ai_transport_failure"
        row["checker_message"] = str(exc)
        _mark_case_step_status(row, "ai_transport", "failure")
        _write_text(case_dir / "failure.txt", str(exc))
        artifact = str((case_dir / "failure.txt").relative_to(run_dir))
        if transport is None:
            transport_state = capture_chatgpt_transport_diagnostics(session)
            _write_json(case_dir / "transport-state.json", transport_state)
            export_chatgpt_transport_artifacts(session, case_dir)
            _apply_transport_metrics(row, transport_state)
            artifact = str((case_dir / "transport-state.json").relative_to(run_dir))
        _append_case_event(
            root_events_path,
            case_events_path,
            run_id=run_dir.name,
            case_id=sample.case_id,
            stage="ai_transport",
            status="failure",
            duration_ms=0.0,
            failure_class=row["failure_class"],
            message=str(exc),
            artifact=artifact,
        )
        chunk_result["status"] = "ABORTED"
        chunk_result["finished_at"] = _timestamp()
        chunk_result["guard_trip_reason"] = str(exc)
        chunk_result["guard_trip_stage"] = "ai_transport"
        chunk_result["failed_case_id"] = sample.case_id
        state["guard_trip_reason"] = str(exc)
        state["guard_trip_stage"] = f"{chunk_name}:ai_transport"
        state["single_session_browser_relaunches"] = max(
            int(state["single_session_browser_relaunches"]),
            int(row.get("session_relaunches", 0)),
        )
        case_rows.append(row)
        return state

    _finish_release_gate_case(
        row=row,
        sample=sample,
        case_dir=case_dir,
        case_events_path=case_events_path,
        run_dir=run_dir,
        root_events_path=root_events_path,
        mode=mode,
        base_url=base_url,
    )
    if row["failure_class"] is not None:
        chunk_result["status"] = "FAIL"
    case_rows.append(row)
    if index == total_samples:
        if chunk_result["completed_chat_count"] == chunk_result["planned_chat_count"]:
            chunk_result["finished_at"] = _timestamp()
            if chunk_result["status"] == "RUNNING":
                chunk_result["status"] = "PASS"
        return state
    _apply_pacing(
        sleep_impl=sleep_impl,
        progress=progress,
        cooldown_schedule=cooldown_schedule,
        chunk_name=chunk_name,
        case_id=sample.case_id,
        completed_chat_count=int(state["completed_chat_count"]),
    )
    if chunk_result["completed_chat_count"] == chunk_result["planned_chat_count"]:
        chunk_result["finished_at"] = _timestamp()
        if chunk_result["status"] == "RUNNING":
            chunk_result["status"] = "PASS"
        if chunk_result["cooldown_after_seconds"] > 0:
            _record_cooldown(
                cooldown_schedule=cooldown_schedule,
                sleep_impl=sleep_impl,
                seconds=float(chunk_result["cooldown_after_seconds"]),
                cooldown_type="chunk",
                chunk_name=chunk_name,
                case_id=sample.case_id,
                completed_chat_count=int(state["completed_chat_count"]),
                progress=progress,
            )
    return state


def _finish_release_gate_case(
    *,
    row: dict[str, Any],
    sample: PreparedSample,
    case_dir: Path,
    case_events_path: Path,
    run_dir: Path,
    root_events_path: Path,
    mode: str,
    base_url: str,
) -> None:
    yaml_candidate = normalize_yaml_candidate((case_dir / "ai-raw.txt").read_text(encoding="utf-8"))
    _write_text(case_dir / "yaml-candidate.yaml", yaml_candidate)
    if not yaml_candidate or "report_content:" not in yaml_candidate:
        row["status"] = "failure"
        row["failure_class"] = "yaml_extract_failure"
        row["checker_message"] = "The AI reply did not contain a usable report_content YAML block."
        _mark_case_step_status(row, "yaml_extract", "failure")
        _write_text(case_dir / "failure.txt", row["checker_message"])
        _append_case_event(
            root_events_path,
            case_events_path,
            run_id=run_dir.name,
            case_id=sample.case_id,
            stage="yaml_extract",
            status="failure",
            duration_ms=0.0,
            failure_class=row["failure_class"],
            message=row["checker_message"],
            artifact=str((case_dir / "yaml-candidate.yaml").relative_to(run_dir)),
        )
        return
    _mark_case_step_status(row, "yaml_extract", "success")
    _append_case_event(
        root_events_path,
        case_events_path,
        run_id=run_dir.name,
        case_id=sample.case_id,
        stage="yaml_extract",
        status="success",
        duration_ms=0.0,
        message="Extracted a report_content YAML candidate.",
        artifact=str((case_dir / "yaml-candidate.yaml").relative_to(run_dir)),
    )

    checker_payload = _run_checker_with_retry(
        mode=mode,
        base_url=base_url,
        yaml_candidate=yaml_candidate,
    )
    _write_json(case_dir / "checker.json", checker_payload)
    manifest_guard_payload = validate_yaml_candidate_against_manifest(
        yaml_candidate,
        manifest=sample.manifest,
    )
    _write_json(case_dir / "manifest-guard.json", manifest_guard_payload)
    row["checker_ok"] = bool(checker_payload.get("ok"))
    row["checker_message"] = str(checker_payload.get("message", ""))
    checker_summary = checker_payload.get("summary", {}) or {}
    row["blocking_issue_count"] = int(checker_summary.get("blocking_issue_count", 0))
    row["warning_count"] = int(checker_summary.get("warning_count", 0))
    if is_yaml_extract_failure(checker_payload):
        row["status"] = "failure"
        row["failure_class"] = "yaml_extract_failure"
        _mark_case_step_status(row, "checker", "failure")
    elif not row["checker_ok"] or row["blocking_issue_count"] > 0:
        row["status"] = "failure"
        row["failure_class"] = "checker_failure"
        _mark_case_step_status(row, "checker", "failure")
    elif not bool(manifest_guard_payload.get("ok")):
        row["status"] = "failure"
        row["failure_class"] = "checker_failure"
        row["checker_ok"] = False
        row["checker_message"] = str(manifest_guard_payload.get("message", ""))
        row["blocking_issue_count"] = max(
            row["blocking_issue_count"],
            len(list(manifest_guard_payload.get("errors", []) or [])),
        )
        _mark_case_step_status(row, "checker", "failure")
    else:
        _mark_case_step_status(row, "checker", "success")
    _append_case_event(
        root_events_path,
        case_events_path,
        run_id=run_dir.name,
        case_id=sample.case_id,
        stage="checker",
        status="success" if row["failure_class"] is None else "failure",
        duration_ms=0.0,
        failure_class=row["failure_class"],
        message=row["checker_message"],
        artifact=str(
            (
                case_dir / (
                    "manifest-guard.json"
                    if row["failure_class"] == "checker_failure"
                    and not bool(manifest_guard_payload.get("ok"))
                    else "checker.json"
                )
            ).relative_to(run_dir)
        ),
    )
    if row["failure_class"] is not None:
        return

    generate_payload, pptx_bytes = _run_generate_with_retry(
        mode=mode,
        base_url=base_url,
        payload_yaml=yaml_candidate,
        image_ref_count=sample.image_ref_count,
    )
    _write_json(case_dir / "generate.json", generate_payload)
    row["generate_ok"] = bool(generate_payload.get("ok"))
    if not row["generate_ok"] or not pptx_bytes:
        row["status"] = "failure"
        row["failure_class"] = "generate_failure"
        _mark_case_step_status(row, "generate", "failure")
        _append_case_event(
            root_events_path,
            case_events_path,
            run_id=run_dir.name,
            case_id=sample.case_id,
            stage="generate",
            status="failure",
            duration_ms=0.0,
            failure_class=row["failure_class"],
            message=str(generate_payload.get("message", "Generation failed.")),
            artifact=str((case_dir / "generate.json").relative_to(run_dir)),
        )
        return
    artifact_path = case_dir / "artifact.pptx"
    artifact_path.write_bytes(pptx_bytes)
    row["artifact_pptx"] = str(artifact_path)
    _mark_case_step_status(row, "generate", "success")
    _append_case_event(
        root_events_path,
        case_events_path,
        run_id=run_dir.name,
        case_id=sample.case_id,
        stage="generate",
        status="success",
        duration_ms=0.0,
        message="Generated PPTX artifact.",
        artifact=str(artifact_path.relative_to(run_dir)),
    )

    inspection_payload = inspect_pptx_artifact(artifact_path)
    _write_json(case_dir / "pptx-inspection.json", inspection_payload)
    row["pptx_openable"] = bool(inspection_payload.get("openable"))
    row["slide_count"] = int(inspection_payload.get("slide_count", 0))
    row["shape_count"] = int(inspection_payload.get("shape_count", 0))
    row["image_count"] = int(inspection_payload.get("image_count", 0))
    if not row["pptx_openable"]:
        row["status"] = "failure"
        row["failure_class"] = "pptx_inspection_failure"
        _mark_case_step_status(row, "pptx_inspection", "failure")
    else:
        _mark_case_step_status(row, "pptx_inspection", "success")
    _append_case_event(
        root_events_path,
        case_events_path,
        run_id=run_dir.name,
        case_id=sample.case_id,
        stage="pptx_inspection",
        status="success" if row["failure_class"] is None else "failure",
        duration_ms=0.0,
        failure_class=row["failure_class"],
        message=str(inspection_payload.get("message", "PPTX inspection complete.")),
        artifact=str((case_dir / "pptx-inspection.json").relative_to(run_dir)),
    )


def _build_release_gate_summary(
    *,
    run_config: dict[str, Any],
    cases: list[dict[str, Any]],
    preflight: dict[str, Any] | None,
    health: dict[str, Any] | None,
    session_check: dict[str, Any] | None,
    started_at: str,
    finished_at: str,
    chunk_results: list[dict[str, Any]],
    cooldown_schedule: list[dict[str, Any]],
    completed_chat_count: int,
    guard_trip_reason: str,
    guard_trip_stage: str,
    single_session_browser_relaunches: int,
) -> dict[str, Any]:
    base_summary = build_summary_payload(
        run_config=run_config,
        cases=cases,
        preflight=preflight,
        health=health,
        session_check=session_check,
        started_at=started_at,
        finished_at=finished_at,
    )
    return build_summary_payload(
        run_config=run_config,
        cases=cases,
        preflight=preflight,
        health=health,
        session_check=session_check,
        started_at=started_at,
        finished_at=finished_at,
        summary_overrides={
            "runbook": RELEASE_GATE_RUNBOOK,
            "planned_chat_count": len(prepare_release_gate_samples()),
            "completed_chat_count": completed_chat_count,
            "chunk_results": [dict(item) for item in chunk_results],
            "cooldown_schedule_applied": list(cooldown_schedule),
            "guard_trip_reason": guard_trip_reason,
            "guard_trip_stage": guard_trip_stage,
            "single_session_browser_relaunches": single_session_browser_relaunches,
            "message": _release_gate_message(
                base_summary["overall_status"],
                session_check_only=bool(run_config.get("session_check_only")),
                guard_trip_reason=guard_trip_reason,
            ),
        },
    )


def _release_gate_message(
    overall_status: str,
    *,
    session_check_only: bool,
    guard_trip_reason: str,
) -> str:
    if session_check_only:
        return _overall_message(overall_status, session_check_only=True)
    if guard_trip_reason:
        return f"Release gate stopped after a ChatGPT transport guard trip: {guard_trip_reason}"
    return _overall_message(overall_status, session_check_only=False)


def _initial_chunk_results() -> list[dict[str, Any]]:
    return [
        {
            "index": chunk.index,
            "name": chunk.name,
            "label": chunk.label,
            "planned_chat_count": len(chunk.case_ids),
            "completed_chat_count": 0,
            "status": "PENDING",
            "cooldown_after_seconds": chunk.cooldown_after_seconds,
            "case_ids": list(chunk.case_ids),
            "started_at": None,
            "finished_at": None,
            "guard_trip_reason": "",
            "guard_trip_stage": "",
        }
        for chunk in build_release_gate_plan()
    ]


def _block_chunk_results(
    chunk_results: list[dict[str, Any]],
    *,
    reason: str,
    blocked_status: str = "BLOCKED",
    from_chunk_index: int = 1,
) -> list[dict[str, Any]]:
    for item in chunk_results:
        if int(item["index"]) >= from_chunk_index and item["status"] == "PENDING":
            item["status"] = blocked_status
            item["guard_trip_reason"] = reason if blocked_status == "BLOCKED" else ""
    return chunk_results


def _apply_pacing(
    *,
    sleep_impl: Callable[[float], None],
    progress: Callable[[str], None] | None,
    cooldown_schedule: list[dict[str, Any]],
    chunk_name: str,
    case_id: str,
    completed_chat_count: int,
) -> None:
    _record_cooldown(
        cooldown_schedule=cooldown_schedule,
        sleep_impl=sleep_impl,
        seconds=INTER_CASE_IDLE_SECONDS,
        cooldown_type="inter_case",
        chunk_name=chunk_name,
        case_id=case_id,
        completed_chat_count=completed_chat_count,
        progress=progress,
    )
    if completed_chat_count > 0 and completed_chat_count % 3 == 0:
        _record_cooldown(
            cooldown_schedule=cooldown_schedule,
            sleep_impl=sleep_impl,
            seconds=TRIPLE_CASE_IDLE_SECONDS,
            cooldown_type="triple_case",
            chunk_name=chunk_name,
            case_id=case_id,
            completed_chat_count=completed_chat_count,
            progress=progress,
        )


def _record_cooldown(
    *,
    cooldown_schedule: list[dict[str, Any]],
    sleep_impl: Callable[[float], None],
    seconds: float,
    cooldown_type: str,
    chunk_name: str,
    case_id: str,
    completed_chat_count: int,
    progress: Callable[[str], None] | None,
) -> None:
    cooldown_schedule.append(
        {
            "type": cooldown_type,
            "seconds": int(seconds),
            "chunk_name": chunk_name,
            "after_case_id": case_id,
            "after_chat_count": completed_chat_count,
        }
    )
    _report_progress(
        progress,
        f"[release-gate] cooldown type={cooldown_type} seconds={int(seconds)} after_chat={completed_chat_count} chunk={chunk_name}",
    )
    if seconds > 0:
        sleep_impl(seconds)


def _write_chunk_artifacts(run_dir: Path, chunk_results: list[dict[str, Any]]) -> None:
    payload = {
        "runbook": RELEASE_GATE_RUNBOOK,
        "chunks": chunk_results,
    }
    _write_json(run_dir / "chunk-results.json", payload)
    lines = [
        "# Release Gate Chunk Results",
        "",
        f"- Runbook: `{RELEASE_GATE_RUNBOOK}`",
        "",
    ]
    for chunk in chunk_results:
        lines.append(
            f"- `{chunk['name']}` `{chunk['status']}` | completed={chunk['completed_chat_count']}/{chunk['planned_chat_count']} | cooldown_after={chunk['cooldown_after_seconds']}s"
        )
        if chunk.get("guard_trip_reason"):
            lines.append(f"  - guard: {chunk['guard_trip_reason']}")
    lines.append("")
    _write_text(run_dir / "chunk-results.md", "\n".join(lines))
