"""FastAPI application for the public Autoreport demo."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.background import BackgroundTask

from autoreport.engine.generator import generate_report_from_mapping
from autoreport.loader import parse_yaml_text
from autoreport.template_flow import (
    materialize_authoring_payload,
    detect_payload_kind,
    get_built_in_contract,
    materialize_report_payload,
    serialize_document,
)
from autoreport.validator import ValidationError


LOGGER = logging.getLogger("autoreport.web")
MEDIA_TYPE_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
ALLOWED_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg"}

_BUILT_IN_CONTRACT = get_built_in_contract()

DEFAULT_CONTRACT_YAML = serialize_document(
    _BUILT_IN_CONTRACT.to_dict(),
    fmt="yaml",
).strip()
AI_DRAFT_PROMPT_YAML = """
# Paste this brief into another AI and ask it to fill the report_content draft below.
# Goal: draft slide-ready content for Autoreport. The app will normalize report_content
# into authoring_payload and then compile the runtime report_payload automatically.
# How Autoreport uses this draft:
# - Each item in report_content.slides becomes one deck slide.
# - The number of slide entries is the number of content slides in the deck.
# - pattern_id selects the PPT layout pattern, so it must come from template_contract.
# - In report_content, kind is optional when pattern_id already matches template_contract.
# - slots.title / slots.body_1 / slots.image_* / slots.caption_* map to template placeholders.
# Rules for the other AI:
# 1. Return the final answer as one fenced ```yaml code block.
# 2. Inside that code block, keep the top-level key as report_content.
# 3. Do not write any prose before or after the fenced YAML block.
# 4. Do not open a second code block and do not split the YAML across plain text and code.
# 5. Do not declare the total slide count anywhere. Autoreport infers it from slides[*].
# 6. Choose pattern_id values from the template contract.
# 7. Put narrative text into slots.body_1.
# 8. For image slides, describe the desired visual in slots.image_1 / image_2 / image_3.
# 9. Actual image files are uploaded later in the web app or passed as CLI paths.
# 10. If the template contract exposes 2-image or 3-image patterns, use the matching pattern_id.
report_content:
  title_slide:
    pattern_id: cover.editorial
    slots:
      title: Replace with the deck title
      subtitle_1: |
        Replace with a concise subtitle
  contents_slide:
    pattern_id: contents.editorial
    slots:
      title: Contents
      body_1: |
        1. Add the first section title
        2. Add the second section title
  slides:
    - pattern_id: text.editorial
      slots:
        title: First section title
        body_1: |
          Write the main narrative for this slide.
    - pattern_id: text_image.editorial
      slots:
        title: Visual proof
        body_1: |
          Explain what the visual should prove.
        image_1: Describe the image the next AI should source or create.
        caption_1: Optional caption
""".strip()
app = FastAPI(
    title="Autoreport Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_demo_html() -> str:
    contract_json = json.dumps(DEFAULT_CONTRACT_YAML)
    draft_prompt_json = json.dumps(AI_DRAFT_PROMPT_YAML)
    compiled_json = json.dumps("")
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Autoreport Demo</title>
    <style>
      :root {
        --bg: #f4f1e8;
        --surface: #ffffff;
        --panel: #f8fafc;
        --text: #172033;
        --muted: #5b687a;
        --accent: #0b6a58;
        --accent-soft: #e8f8f2;
        --border: #d5deea;
        --shadow: 0 24px 52px rgba(15, 23, 42, 0.08);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top right, rgba(11,106,88,0.08), transparent 24%),
          linear-gradient(180deg, rgba(11,106,88,0.05), transparent 32%),
          var(--bg);
        color: var(--text);
        font-family: "Segoe UI", Arial, sans-serif;
      }
      main { max-width: 1420px; margin: 0 auto; padding: 36px 24px 56px; }
      h1 { margin: 0 0 12px; text-align: center; color: var(--accent); font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: -0.04em; }
      .hero-copy { max-width: 880px; margin: 0 auto 28px; text-align: center; color: var(--muted); line-height: 1.7; }
      .card { background: var(--surface); border: 1px solid rgba(15,23,42,0.06); border-radius: 24px; box-shadow: var(--shadow); padding: 28px; }
      .workspace { display: grid; grid-template-columns: minmax(760px, 1.6fr) 340px; gap: 20px; align-items: start; }
      .panel, .rail-box { min-width: 0; }
      .rail { display: grid; gap: 16px; align-self: start; position: sticky; top: 20px; }
      .panel h2, .rail-box h2, .upload-box h2 { margin: 0 0 8px; font-size: 1rem; }
      .panel-copy, .footnote { color: var(--muted); line-height: 1.6; font-size: 0.95rem; }
      textarea {
        width: 100%;
        min-height: 420px;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        background: var(--panel);
        color: var(--text);
        font: 0.9rem/1.6 "Cascadia Mono", Consolas, monospace;
        resize: vertical;
      }
      textarea[readonly] { opacity: 0.94; }
      .primary-actions, .copy-actions, .mini-actions { display: grid; gap: 10px; }
      .primary-actions { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 16px; }
      .copy-actions { margin-top: 14px; }
      button {
        border: none;
        border-radius: 999px;
        padding: 10px 16px;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }
      .ghost { background: var(--accent-soft); color: var(--accent); }
      .primary { width: 100%; padding: 14px 18px; border-radius: 16px; background: var(--accent); color: #fff; }
      .rail-box, .upload-box, details { border: 1px solid var(--border); border-radius: 18px; background: var(--panel); padding: 18px; }
      .upload-box { margin-top: 18px; }
      details { margin-top: 18px; }
      details summary { cursor: pointer; font-weight: 700; color: var(--text); }
      .upload-list, .status-errors, .status-hints, .howto-list { margin: 12px 0 0; padding-left: 18px; line-height: 1.6; }
      .upload-list { list-style: none; padding: 0; display: grid; gap: 10px; }
      .upload-item { border: 1px solid var(--border); border-radius: 14px; background: #fff; padding: 12px; }
      .upload-ref { display: inline-flex; min-width: 74px; justify-content: center; padding: 4px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font: 0.82rem/1.2 "Cascadia Mono", Consolas, monospace; font-weight: 700; margin-right: 8px; }
      .howto-list { color: var(--muted); }
      .status-errors { color: #b91c1c; }
      .status-hints { color: var(--accent); }
      code { font-family: "Cascadia Mono", Consolas, monospace; }
      @media (max-width: 1240px) {
        .workspace { grid-template-columns: 1fr; }
        .rail { position: static; }
      }
      @media (max-width: 980px) {
        .primary-actions { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Draft the deck with AI and generate an Autoreport PPTX.</h1>
      <p class="hero-copy">
        Give one prompt package to another AI, let it draft as many slides as needed,
        paste the returned <code>report_content</code>, and generate the deck.
      </p>
      <section class="card">
        <div class="workspace">
          <div class="panel">
            <h2>AI Draft Input</h2>
            <p class="panel-copy">
              Paste either a high-level <code>report_content</code> draft from another AI
              or a ready-made <code>authoring_payload</code>. The app normalizes drafts into
              <code>authoring_payload</code> automatically. You do not need to declare a total
              slide count anywhere; the deck length is inferred from the slides you include.
            </p>
            <textarea id="payload-yaml" aria-label="Working draft"></textarea>
            <div class="primary-actions">
              <button id="copy-handoff" class="ghost" type="button">Copy AI Package</button>
              <button id="refresh-compiled" class="ghost" type="button">Normalize Draft</button>
              <button id="generate-button" class="primary" type="button">Generate PPTX</button>
            </div>
            <details>
              <summary>Optional: View Template Contract</summary>
              <p class="panel-copy">
                Share this with another AI so it can choose valid <code>pattern_id</code>
                values and image layouts.
              </p>
              <textarea id="template-contract" readonly aria-label="Template contract"></textarea>
            </details>
            <details>
              <summary>Advanced Debug: Compiled Report Payload</summary>
              <p class="panel-copy">
                This preview shows the compiled runtime payload that the engine will execute.
              </p>
              <textarea id="compiled-payload" readonly aria-label="Compiled report payload"></textarea>
            </details>
            <div class="upload-box">
              <h2>Image Uploads</h2>
              <p class="panel-copy">
                If the AI draft asks for images, upload the real files here and replace the
                descriptive <code>slots.image_*</code> text with refs such as
                <code>image_1</code>.
              </p>
              <input id="image-files" type="file" multiple accept=".png,.jpg,.jpeg">
              <ul id="upload-list" class="upload-list"></ul>
            </div>
          </div>
          <aside class="rail">
            <div class="rail-box">
              <h2>How To Use</h2>
              <p class="panel-copy">
                This page is meant for one simple flow, not manual slide-by-slide editing.
              </p>
              <ul class="howto-list">
                <li>Copy the AI package and send it to another AI.</li>
                <li>Ask it to return <code>report_content</code> with as many slides as you want.</li>
                <li>Paste the YAML back into the big editor.</li>
                <li>If visuals are needed, upload the real image files here and swap in uploaded refs.</li>
                <li>Press <code>Generate PPTX</code>.</li>
              </ul>
              <div class="copy-actions">
                <button id="reset-draft" class="ghost" type="button">Reset To AI Draft Prompt</button>
                <button id="copy-draft-prompt" class="ghost" type="button">Copy AI Draft Prompt</button>
                <button id="copy-contract" class="ghost" type="button">Copy Template Contract</button>
                <button id="copy-handoff-secondary" class="ghost" type="button">Copy AI Package</button>
              </div>
              <div id="status-message" class="panel-copy">
                The built-in editorial contract and AI draft prompt are loaded. Copy the package to another AI, then paste the returned draft here.
              </div>
              <ul id="status-errors" class="status-errors"></ul>
              <ul id="status-hints" class="status-hints"></ul>
              <p class="footnote">
                Current scope: built-in editorial template, AI-draft input, dynamic slide counts, uploaded image refs, optional compiled preview, instant download.
              </p>
            </div>
          </aside>
        </div>
      </section>
    </main>
    <script>
      const CONTRACT_YAML = __CONTRACT_JSON__;
      const AI_DRAFT_PROMPT = __DRAFT_PROMPT_JSON__;
      const DEFAULT_COMPILED = __COMPILED_JSON__;
      const contractNode = document.getElementById("template-contract");
      const payloadNode = document.getElementById("payload-yaml");
      const compiledNode = document.getElementById("compiled-payload");
      const uploadList = document.getElementById("upload-list");
      const fileInput = document.getElementById("image-files");
      const statusMessage = document.getElementById("status-message");
      const statusErrors = document.getElementById("status-errors");
      const statusHints = document.getElementById("status-hints");

      let uploadedRefs = [];

      function setStatus(message, errors = [], hints = []) {
        statusMessage.textContent = message;
        statusErrors.innerHTML = "";
        statusHints.innerHTML = "";
        for (const error of errors) {
          const li = document.createElement("li");
          li.textContent = error;
          statusErrors.appendChild(li);
        }
        for (const hint of hints) {
          const li = document.createElement("li");
          li.textContent = hint;
          statusHints.appendChild(li);
        }
      }

      async function copyTextToClipboard(label, text) {
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
          } else {
            const helper = document.createElement("textarea");
            helper.value = text;
            helper.setAttribute("readonly", "readonly");
            helper.style.position = "absolute";
            helper.style.left = "-9999px";
            document.body.appendChild(helper);
            helper.select();
            document.execCommand("copy");
            helper.remove();
          }
          setStatus(`${label} copied to the clipboard.`, [], ["Paste it into the next AI turn together with any required image files."]);
        } catch (error) {
          setStatus(`Could not copy ${label.toLowerCase()} automatically.`, [], ["Select the text manually and copy it from the page."]);
        }
      }

      function buildAiHandoffPackage() {
        const uploadNotes = uploadedRefs.length
          ? uploadedRefs.map((item) => `- ${item.ref}: ${item.file.name}`).join("\\n")
          : "- none";
        return [
          "# Autoreport AI Handoff",
          "",
          "Start with the AI draft prompt below, then include the template contract.",
          "The other AI should return report_content. Autoreport will normalize it into authoring_payload later.",
          "",
          "## AI Draft Prompt",
          "```yaml",
          AI_DRAFT_PROMPT,
          "```",
          "",
          "## Template Contract",
          "```yaml",
          contractNode.value.trim(),
          "```",
          "",
          "## Current Working Draft",
          "```yaml",
          payloadNode.value.trim(),
          "```",
          "",
          "## Uploaded Image Refs In This Browser Session",
          uploadNotes,
        ].join("\\n");
      }

      function renderUploads() {
        uploadList.innerHTML = "";
        if (!uploadedRefs.length) {
          const li = document.createElement("li");
          li.className = "upload-item";
          li.textContent = "No uploaded files yet.";
          uploadList.appendChild(li);
          return;
        }

        for (const item of uploadedRefs) {
          const li = document.createElement("li");
          li.className = "upload-item";
          const label = document.createElement("div");
          label.innerHTML = `<span class="upload-ref">${item.ref}</span>${item.file.name}`;
          const actions = document.createElement("div");
          actions.className = "mini-actions";

          const insertRefButton = document.createElement("button");
          insertRefButton.type = "button";
          insertRefButton.className = "ghost";
          insertRefButton.textContent = "Insert Ref";
          insertRefButton.addEventListener("click", () => {
            const start = payloadNode.selectionStart ?? payloadNode.value.length;
            const end = payloadNode.selectionEnd ?? payloadNode.value.length;
            payloadNode.setRangeText(item.ref, start, end, "end");
            setStatus(`${item.ref} was inserted at the current cursor.`);
          });

          actions.append(insertRefButton);
          li.append(label, actions);
          uploadList.appendChild(li);
        }
      }

      async function postPayload(url) {
        const formData = new FormData();
        formData.append("payload_yaml", payloadNode.value.trim());
        const manifest = uploadedRefs.map((item) => ({
          ref: item.ref,
          field_name: item.ref,
          filename: item.file.name,
        }));
        formData.append("image_manifest", JSON.stringify(manifest));
        for (const item of uploadedRefs) {
          formData.append(item.ref, item.file, item.file.name);
        }
        return fetch(url, { method: "POST", body: formData });
      }

      async function refreshCompiledPreview() {
        if (!payloadNode.value.trim()) {
          setStatus("The working draft is empty.", [], ["Reset to the AI draft prompt to begin."]);
          return;
        }
        setStatus("Normalizing the draft and compiling the runtime report payload...");
        const response = await postPayload("/api/compile");
        const payload = await response.json();
        if (!response.ok) {
          setStatus(payload.message || "Compilation failed.", payload.errors || [], payload.hints || []);
          return;
        }
        if (payload.normalized_authoring_yaml) {
          payloadNode.value = payload.normalized_authoring_yaml;
        }
        compiledNode.value = payload.compiled_yaml;
        setStatus(
          payload.payload_kind === "content"
            ? "AI draft normalized into authoring_payload successfully."
            : `Draft accepted as ${payload.payload_kind} and compiled successfully.`,
          [],
          payload.hints && payload.hints.length
            ? payload.hints
            : [`Compiled slides: ${payload.slide_count}`]
        );
      }

      contractNode.value = CONTRACT_YAML;
      payloadNode.value = AI_DRAFT_PROMPT;
      compiledNode.value = "";
      renderUploads();

      document.getElementById("reset-draft").addEventListener("click", () => {
        payloadNode.value = AI_DRAFT_PROMPT;
        compiledNode.value = "";
        setStatus(
          "AI draft prompt restored.",
          [],
          ["Send this prompt together with the template contract to another AI, then paste the returned report_content draft back here."]
        );
      });

      document.getElementById("refresh-compiled").addEventListener("click", refreshCompiledPreview);
      document.getElementById("copy-draft-prompt").addEventListener("click", () => copyTextToClipboard("AI draft prompt", AI_DRAFT_PROMPT));
      document.getElementById("copy-contract").addEventListener("click", () => copyTextToClipboard("Template contract", contractNode.value.trim()));
      document.getElementById("copy-handoff").addEventListener("click", () => copyTextToClipboard("AI handoff package", buildAiHandoffPackage()));
      document.getElementById("copy-handoff-secondary").addEventListener("click", () => copyTextToClipboard("AI handoff package", buildAiHandoffPackage()));

      fileInput.addEventListener("change", () => {
        uploadedRefs = Array.from(fileInput.files || []).map((file, index) => ({
          ref: `image_${index + 1}`,
          file,
        }));
        renderUploads();
        if (uploadedRefs.length) {
          setStatus(
            "Uploads are ready.",
            [],
            [`Available refs: ${uploadedRefs.map((item) => item.ref).join(", ")}`]
          );
        } else {
          setStatus("No uploads selected.");
        }
      });

      document.getElementById("generate-button").addEventListener("click", async () => {
        if (!payloadNode.value.trim()) {
          setStatus("Generation failed. Please provide payload YAML.", [], ["Reset to the AI draft prompt to begin."]);
          return;
        }
        const button = document.getElementById("generate-button");
        button.disabled = true;
        setStatus("Validating the payload and generating your Autoreport deck...");
        try {
          const response = await postPayload("/api/generate");
          if (!response.ok) {
            const payload = await response.json();
            button.disabled = false;
            setStatus(payload.message || "Generation failed.", payload.errors || [], payload.hints || []);
            return;
          }
          const blob = await response.blob();
          const downloadUrl = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = downloadUrl;
          anchor.download = "autoreport_demo.pptx";
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(downloadUrl);
          button.disabled = false;
          setStatus("Generation complete. Your Autoreport deck download should begin shortly.");
        } catch (error) {
          button.disabled = false;
          setStatus("A network error occurred. Please try again in a moment.");
        }
      });
    </script>
  </body>
</html>""".replace("__CONTRACT_JSON__", contract_json).replace("__DRAFT_PROMPT_JSON__", draft_prompt_json).replace("__COMPILED_JSON__", compiled_json)


INDEX_HTML = _render_demo_html()


def _cleanup_temp_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _log_result(
    *,
    request_id: str,
    result: str,
    started_at: float,
    error_type: str | None = None,
) -> None:
    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    LOGGER.info(
        "request_id=%s result=%s duration_ms=%s error_type=%s",
        request_id,
        result,
        duration_ms,
        error_type or "none",
    )


def _error_response(
    *,
    status_code: int,
    error_type: str,
    message: str,
    errors: list[str] | None = None,
) -> JSONResponse:
    payload: dict[str, object] = {
        "error_type": error_type,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors
    return JSONResponse(status_code=status_code, content=payload)


def _collect_missing_uploaded_image_errors(
    raw_data: dict[str, object],
    *,
    available_image_refs: set[str],
) -> list[str]:
    payload_kind = detect_payload_kind(raw_data)
    if payload_kind not in {"authoring", "content"}:
        return []

    authoring_payload, _ = materialize_authoring_payload(
        raw_data,
        _BUILT_IN_CONTRACT,
        available_image_refs=available_image_refs,
        enforce_image_refs=False,
    )
    errors: list[str] = []
    for slide in authoring_payload.slides:
        for image in slide.assets.images:
            if image.path is not None or image.ref is None:
                continue
            if image.ref not in available_image_refs:
                errors.append(
                    f"Slide {slide.slide_no} needs an uploaded image for ref '{image.ref}'. "
                    "Upload the matching file below before generating, or replace the draft image note with a real file path/ref."
                )
    return errors


@app.get("/", response_class=HTMLResponse)
def demo_page() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.post("/api/compile")
async def compile_demo_payload(request: Request) -> JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        raw_data, image_refs, temp_dir_path = await _parse_request_payload(request)
        payload_kind = detect_payload_kind(raw_data)
        normalized_authoring_yaml: str | None = None
        hints: list[str] = []

        if payload_kind in {"authoring", "content"}:
            normalized_authoring, hints = materialize_authoring_payload(
                raw_data,
                _BUILT_IN_CONTRACT,
                available_image_refs=image_refs.keys(),
                enforce_image_refs=False,
            )
            normalized_authoring_yaml = serialize_document(
                normalized_authoring.to_dict(),
                fmt="yaml",
            ).strip()
            compiled_payload = materialize_report_payload(
                normalized_authoring.to_dict(),
                _BUILT_IN_CONTRACT,
                available_image_refs=image_refs.keys(),
                enforce_image_refs=False,
            )
        else:
            compiled_payload = materialize_report_payload(
                raw_data,
                _BUILT_IN_CONTRACT,
                available_image_refs=image_refs.keys(),
                enforce_image_refs=False,
            )
    except yaml.YAMLError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="yaml_parse_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="validation_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Payload validation failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="internal_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    return JSONResponse(
        {
            "payload_kind": payload_kind,
            "normalized_authoring_yaml": normalized_authoring_yaml,
            "compiled_yaml": serialize_document(compiled_payload.to_dict(), fmt="yaml").strip(),
            "slide_count": len(compiled_payload.slides),
            "hints": hints,
        }
    )


@app.post("/api/generate", response_model=None)
async def generate_demo_report(request: Request) -> FileResponse | JSONResponse:
    request_id = uuid4().hex
    started_at = perf_counter()
    temp_dir_path: Path | None = None

    try:
        raw_data, image_refs, temp_dir_path = await _parse_request_payload(
            request,
            keep_temp_dir=True,
        )
        missing_image_errors = _collect_missing_uploaded_image_errors(
            raw_data,
            available_image_refs=set(image_refs.keys()),
        )
        if missing_image_errors:
            _log_result(request_id=request_id, result="error", started_at=started_at, error_type="validation_error")
            _cleanup_temp_dir(temp_dir_path)
            return _error_response(
                status_code=422,
                error_type="validation_error",
                message="Payload validation failed.",
                errors=missing_image_errors,
            )
        output_path = temp_dir_path / "autoreport_demo.pptx"
        generated_path = generate_report_from_mapping(
            raw_data,
            output_path=output_path,
            image_refs=image_refs,
        )
    except yaml.YAMLError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="yaml_parse_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=400,
            error_type="yaml_parse_error",
            message=f"Failed to parse YAML: {exc}",
        )
    except ValidationError as exc:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="validation_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=422,
            error_type="validation_error",
            message="Payload validation failed.",
            errors=exc.errors,
        )
    except Exception:
        _log_result(request_id=request_id, result="error", started_at=started_at, error_type="internal_error")
        if temp_dir_path is not None:
            _cleanup_temp_dir(temp_dir_path)
        return _error_response(
            status_code=500,
            error_type="internal_error",
            message="An unexpected internal error occurred.",
        )

    _log_result(request_id=request_id, result="success", started_at=started_at)
    return FileResponse(
        path=generated_path,
        media_type=MEDIA_TYPE_PPTX,
        filename="autoreport_demo.pptx",
        background=BackgroundTask(_cleanup_temp_dir, temp_dir_path),
    )


async def _parse_request_payload(
    request: Request,
    *,
    keep_temp_dir: bool = False,
) -> tuple[dict[str, object], dict[str, Path], Path | None]:
    form = await request.form()
    payload_yaml = form.get("payload_yaml")
    image_manifest_raw = form.get("image_manifest", "[]")
    if not isinstance(payload_yaml, str):
        raise ValidationError(["Field 'payload_yaml' is required."])
    if not isinstance(image_manifest_raw, str):
        image_manifest_raw = "[]"

    try:
        image_manifest = json.loads(image_manifest_raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            ["Field 'image_manifest' must be a valid JSON list."]
        ) from exc
    if not isinstance(image_manifest, list):
        raise ValidationError(["Field 'image_manifest' must be a JSON list."])

    temp_dir_path = Path(tempfile.mkdtemp(prefix="autoreport-web-"))
    image_refs = await _collect_uploaded_images(
        form=form,
        image_manifest=image_manifest,
        temp_dir_path=temp_dir_path,
    )
    raw_data = parse_yaml_text(payload_yaml)

    if keep_temp_dir:
        return raw_data, image_refs, temp_dir_path

    _cleanup_temp_dir(temp_dir_path)
    return raw_data, image_refs, None


async def _collect_uploaded_images(
    *,
    form,
    image_manifest: list[object],
    temp_dir_path: Path,
) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    used_refs: set[str] = set()
    for index, item in enumerate(image_manifest):
        if not isinstance(item, dict):
            raise ValidationError(
                [f"Field 'image_manifest[{index}]' must be an object."]
            )
        ref = item.get("ref")
        field_name = item.get("field_name")
        if not isinstance(ref, str) or not ref.strip():
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' must be a non-empty string."]
            )
        if not isinstance(field_name, str) or not field_name.strip():
            raise ValidationError(
                [f"Field 'image_manifest[{index}].field_name' must be a non-empty string."]
            )
        if ref in used_refs:
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' must be unique."]
            )
        upload = form.get(field_name)
        if not (hasattr(upload, "filename") and hasattr(upload, "read")):
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' does not match an uploaded file."]
            )
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED_UPLOAD_SUFFIXES:
            raise ValidationError(
                [f"Field 'image_manifest[{index}].ref' has an unsupported file type."]
            )
        target_path = temp_dir_path / f"{ref}{suffix}"
        content = await upload.read()
        target_path.write_bytes(content)
        refs[ref] = target_path
        used_refs.add(ref)
    return refs
