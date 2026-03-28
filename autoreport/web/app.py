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
    detect_payload_kind,
    get_built_in_contract,
    materialize_report_payload,
    scaffold_payload,
    serialize_document,
)
from autoreport.validator import ValidationError


LOGGER = logging.getLogger("autoreport.web")
MEDIA_TYPE_PPTX = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
ALLOWED_UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg"}

_BUILT_IN_CONTRACT = get_built_in_contract()
_TEXT_ONLY_EXAMPLE_AUTHORING = scaffold_payload(
    _BUILT_IN_CONTRACT,
    include_text_image=False,
)
_FULL_EXAMPLE_AUTHORING = scaffold_payload(
    _BUILT_IN_CONTRACT,
    include_text_image=True,
)

DEFAULT_CONTRACT_YAML = serialize_document(
    _BUILT_IN_CONTRACT.to_dict(),
    fmt="yaml",
).strip()
DEFAULT_PAYLOAD_YAML = serialize_document(
    _TEXT_ONLY_EXAMPLE_AUTHORING.to_dict(),
    fmt="yaml",
).strip()
FULL_EXAMPLE_PAYLOAD_YAML = serialize_document(
    _FULL_EXAMPLE_AUTHORING.to_dict(),
    fmt="yaml",
).strip()
DEFAULT_COMPILED_YAML = serialize_document(
    materialize_report_payload(
        _TEXT_ONLY_EXAMPLE_AUTHORING.to_dict(),
        _BUILT_IN_CONTRACT,
    ).to_dict(),
    fmt="yaml",
).strip()

app = FastAPI(
    title="Autoreport Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_demo_html() -> str:
    contract_json = json.dumps(DEFAULT_CONTRACT_YAML)
    payload_json = json.dumps(DEFAULT_PAYLOAD_YAML)
    image_payload_json = json.dumps(FULL_EXAMPLE_PAYLOAD_YAML)
    compiled_json = json.dumps(DEFAULT_COMPILED_YAML)
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
      main { max-width: 1280px; margin: 0 auto; padding: 40px 18px 54px; }
      h1 { margin: 0 0 12px; text-align: center; color: var(--accent); font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: -0.04em; }
      .hero-copy { max-width: 880px; margin: 0 auto 28px; text-align: center; color: var(--muted); line-height: 1.7; }
      .card { background: var(--surface); border: 1px solid rgba(15,23,42,0.06); border-radius: 24px; box-shadow: var(--shadow); padding: 24px; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
      .controls { display: grid; grid-template-columns: 1fr 320px; gap: 20px; margin-top: 20px; }
      .panel h2, .status-box h2 { margin: 0 0 8px; font-size: 1rem; }
      .panel-copy, .footnote { color: var(--muted); line-height: 1.6; font-size: 0.95rem; }
      textarea {
        width: 100%;
        min-height: 330px;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px;
        background: var(--panel);
        color: var(--text);
        font: 0.9rem/1.6 "Cascadia Mono", Consolas, monospace;
        resize: vertical;
      }
      textarea[readonly] { opacity: 0.94; }
      .actions, .quick-actions, .mini-actions { display: flex; flex-wrap: wrap; gap: 10px; }
      .actions { margin-top: 14px; }
      .quick-actions { margin-top: 16px; }
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
      .upload-box, .status-box, details { border: 1px solid var(--border); border-radius: 18px; background: var(--panel); padding: 18px; }
      details { margin-top: 18px; }
      details summary { cursor: pointer; font-weight: 700; color: var(--text); }
      .upload-list, .summary-list, .status-errors, .status-hints { margin: 12px 0 0; padding-left: 18px; line-height: 1.6; }
      .upload-list { list-style: none; padding: 0; display: grid; gap: 10px; }
      .upload-item { border: 1px solid var(--border); border-radius: 14px; background: #fff; padding: 12px; }
      .upload-ref { display: inline-flex; min-width: 74px; justify-content: center; padding: 4px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font: 0.82rem/1.2 "Cascadia Mono", Consolas, monospace; font-weight: 700; margin-right: 8px; }
      .status-errors { color: #b91c1c; }
      .status-hints { color: var(--accent); }
      code { font-family: "Cascadia Mono", Consolas, monospace; }
      @media (max-width: 980px) {
        .grid, .controls { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Author the deck, inspect the contract, and generate an Autoreport PPTX.</h1>
      <p class="hero-copy">
        The homepage is now authoring-first. Start with <code>authoring_payload</code>,
        keep the template contract visible as reference, and open the advanced panel
        only when you want to inspect the compiled <code>report_payload</code>.
      </p>
      <section class="card">
        <div class="grid">
          <div class="panel">
            <h2>Template Contract</h2>
            <p class="panel-copy">
              This is the built-in editorial capability map. Another AI can read
              <code>slide_patterns</code>, <code>image_count</code>, and
              <code>image_layout</code> here to choose layouts without reverse-engineering raw slots.
            </p>
            <textarea id="template-contract" readonly aria-label="Template contract"></textarea>
          </div>
          <div class="panel">
            <h2>Authoring Payload</h2>
            <p class="panel-copy">
              Describe each slide by intent, context, assets, and layout request.
              The compiler turns this into the runtime <code>report_payload</code> before generation.
            </p>
            <textarea id="payload-yaml" aria-label="Authoring payload"></textarea>
            <div class="actions">
              <button id="load-example" class="ghost" type="button">Load Starter</button>
              <button id="load-image-example" class="ghost" type="button">Load Image Example</button>
              <button id="refresh-compiled" class="ghost" type="button">Refresh Compiled Preview</button>
            </div>
            <div class="quick-actions">
              <button id="insert-text-slide" class="ghost" type="button">Insert Text Slide</button>
              <button id="insert-metrics-slide" class="ghost" type="button">Insert Metrics Slide</button>
              <button id="insert-one-image-slide" class="ghost" type="button">Insert 1-Image Slide</button>
              <button id="insert-two-horizontal-slide" class="ghost" type="button">Insert 2-Image Horizontal</button>
              <button id="insert-three-vertical-slide" class="ghost" type="button">Insert 3-Image Vertical</button>
            </div>
            <details>
              <summary>Advanced Debug: Compiled Report Payload</summary>
              <p class="panel-copy">
                This preview shows the compiled runtime payload that the engine will execute.
              </p>
              <textarea id="compiled-payload" readonly aria-label="Compiled report payload"></textarea>
            </details>
          </div>
        </div>
        <div class="controls">
          <div class="upload-box">
            <h2>Image Uploads</h2>
            <p class="panel-copy">
              Uploaded files become <code>image_1</code>-style refs. Helper actions insert those refs
              into <code>assets.images</code> blocks so the authoring payload stays valid.
            </p>
            <input id="image-files" type="file" multiple accept=".png,.jpg,.jpeg">
            <ul id="upload-list" class="upload-list"></ul>
          </div>
          <div class="status-box">
            <h2>Current Status</h2>
            <div id="status-message" class="panel-copy">
              The built-in editorial contract is loaded. Edit the authoring payload, refresh the compiled preview, or generate the deck.
            </div>
            <ul id="status-errors" class="status-errors"></ul>
            <ul id="status-hints" class="status-hints"></ul>
            <div class="actions" style="margin-top:16px;">
              <button id="generate-button" class="primary" type="button">Generate PPTX</button>
            </div>
            <h2 style="margin-top:18px;">Authoring Summary</h2>
            <ul id="deck-summary" class="summary-list"></ul>
            <p class="footnote">
              Current scope: built-in editorial template, authoring-first homepage, uploaded image refs, compiled preview, instant download.
            </p>
          </div>
        </div>
      </section>
    </main>
    <script>
      const CONTRACT_YAML = __CONTRACT_JSON__;
      const STARTER_PAYLOAD = __PAYLOAD_JSON__;
      const IMAGE_PAYLOAD = __IMAGE_PAYLOAD_JSON__;
      const DEFAULT_COMPILED = __COMPILED_JSON__;
      const contractNode = document.getElementById("template-contract");
      const payloadNode = document.getElementById("payload-yaml");
      const compiledNode = document.getElementById("compiled-payload");
      const uploadList = document.getElementById("upload-list");
      const fileInput = document.getElementById("image-files");
      const statusMessage = document.getElementById("status-message");
      const statusErrors = document.getElementById("status-errors");
      const statusHints = document.getElementById("status-hints");
      const deckSummary = document.getElementById("deck-summary");

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

      function countSlides() {
        return (payloadNode.value.match(/^\\s+- slide_no:/gm) || []).length;
      }

      function nextSlideNo() {
        return countSlides() + 1;
      }

      function currentRefs(count) {
        if (uploadedRefs.length >= count) {
          return uploadedRefs.slice(0, count).map((item) => item.ref);
        }
        const refs = [];
        for (let index = 1; index <= count; index += 1) {
          refs.push(`image_${index}`);
        }
        return refs;
      }

      function appendSlideBlock(block) {
        const trimmed = payloadNode.value.trimEnd();
        if (!trimmed.includes("  slides:")) {
          setStatus(
            "The authoring payload must contain authoring_payload.slides before helper blocks can be inserted.",
            [],
            ["Restore the starter payload if the structure drifted."]
          );
          return false;
        }
        payloadNode.value = `${trimmed}\\n${block}\\n`;
        updateSummary();
        return true;
      }

      function buildTextSlideBlock() {
        const slideNo = nextSlideNo();
        return [
          `  - slide_no: ${slideNo}`,
          "    goal: New Text Slide",
          "    include_in_contents: true",
          "    context:",
          "      summary: Add the key message for this slide.",
          "      bullets:",
          "        - Add one supporting proof point.",
          "    layout_request:",
          "      kind: text",
          "      image_orientation: auto",
        ].join("\\n");
      }

      function buildMetricsSlideBlock() {
        const slideNo = nextSlideNo();
        return [
          `  - slide_no: ${slideNo}`,
          "    goal: New Metrics Slide",
          "    include_in_contents: true",
          "    context:",
          "      metrics:",
          "        - label: Metric label",
          "          value: 10",
          "        - label: Second metric",
          "          value: 24",
          "    layout_request:",
          "      kind: metrics",
          "      image_orientation: auto",
        ].join("\\n");
      }

      function buildImageSlideBlock(count, orientation) {
        const slideNo = nextSlideNo();
        const refs = currentRefs(count);
        return [
          `  - slide_no: ${slideNo}`,
          "    goal: Visual Proof",
          "    include_in_contents: true",
          "    context:",
          "      summary: Add the narrative that should sit with the images.",
          "      bullets:",
          "        - Explain why this visual matters.",
          "      caption: Optional shared caption for the image region.",
          "    assets:",
          "      images:",
          ...refs.map((ref) => `        - ref: ${ref}\\n          fit: contain`),
          "    layout_request:",
          "      kind: text_image",
          `      image_count: ${count}`,
          `      image_orientation: ${orientation}`,
        ].join("\\n");
      }

      function parseAuthoringSummary(text) {
        const slideNos = text.match(/^\\s+- slide_no:\\s*(\\d+)/gm) || [];
        const goals = text.match(/^\\s+goal:\\s*(.+)$/gm) || [];
        const refs = text.match(/^\\s+- ref:\\s*(.+)$/gm) || [];
        return {
          slideCount: slideNos.length,
          goals: goals.map((line) => line.replace(/^\\s+goal:\\s*/, "")),
          refs: refs.map((line) => line.replace(/^\\s+- ref:\\s*/, "")),
        };
      }

      function updateSummary() {
        deckSummary.innerHTML = "";
        const summary = parseAuthoringSummary(payloadNode.value);
        const items = [
          `Authored slides: ${summary.slideCount}`,
          `Slide goals: ${summary.goals.length ? summary.goals.join(" | ") : "none yet"}`,
          `Image refs in payload: ${summary.refs.length ? summary.refs.join(", ") : "none yet"}`,
          `Uploaded refs ready: ${uploadedRefs.length ? uploadedRefs.map((item) => item.ref).join(", ") : "none yet"}`,
        ];
        for (const item of items) {
          const li = document.createElement("li");
          li.textContent = item;
          deckSummary.appendChild(li);
        }
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
            updateSummary();
          });

          const addSlideButton = document.createElement("button");
          addSlideButton.type = "button";
          addSlideButton.className = "ghost";
          addSlideButton.textContent = "Add 1-Image Slide";
          addSlideButton.addEventListener("click", () => {
            if (appendSlideBlock(buildImageSlideBlock(1, "auto"))) {
              setStatus(`A 1-image authoring block using ${item.ref} was appended.`);
            }
          });

          actions.append(insertRefButton, addSlideButton);
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
          setStatus("The authoring payload is empty.", [], ["Load the starter payload to begin."]);
          return;
        }
        setStatus("Compiling the authoring payload into the runtime report payload...");
        const response = await postPayload("/api/compile");
        const payload = await response.json();
        if (!response.ok) {
          setStatus(payload.message || "Compilation failed.", payload.errors || [], payload.hints || []);
          return;
        }
        compiledNode.value = payload.compiled_yaml;
        setStatus(
          `Compiled preview refreshed from the ${payload.payload_kind} input.`,
          [],
          [`Compiled slides: ${payload.slide_count}`]
        );
      }

      contractNode.value = CONTRACT_YAML;
      payloadNode.value = STARTER_PAYLOAD;
      compiledNode.value = DEFAULT_COMPILED;
      updateSummary();
      renderUploads();

      document.getElementById("load-example").addEventListener("click", () => {
        payloadNode.value = STARTER_PAYLOAD;
        compiledNode.value = DEFAULT_COMPILED;
        setStatus("Starter authoring payload restored.");
        updateSummary();
      });

      document.getElementById("load-image-example").addEventListener("click", () => {
        payloadNode.value = IMAGE_PAYLOAD;
        setStatus(
          "Image-capable authoring payload restored.",
          [],
          ["Upload matching image refs, then refresh the compiled preview or generate the deck."]
        );
        updateSummary();
      });

      document.getElementById("refresh-compiled").addEventListener("click", refreshCompiledPreview);
      document.getElementById("insert-text-slide").addEventListener("click", () => appendSlideBlock(buildTextSlideBlock()));
      document.getElementById("insert-metrics-slide").addEventListener("click", () => appendSlideBlock(buildMetricsSlideBlock()));
      document.getElementById("insert-one-image-slide").addEventListener("click", () => appendSlideBlock(buildImageSlideBlock(1, "auto")));
      document.getElementById("insert-two-horizontal-slide").addEventListener("click", () => appendSlideBlock(buildImageSlideBlock(2, "horizontal")));
      document.getElementById("insert-three-vertical-slide").addEventListener("click", () => appendSlideBlock(buildImageSlideBlock(3, "vertical")));
      payloadNode.addEventListener("input", updateSummary);

      fileInput.addEventListener("change", () => {
        uploadedRefs = Array.from(fileInput.files || []).map((file, index) => ({
          ref: `image_${index + 1}`,
          file,
        }));
        renderUploads();
        updateSummary();
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
          setStatus("Generation failed. Please provide payload YAML.", [], ["Load the starter payload to begin."]);
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
</html>""".replace("__CONTRACT_JSON__", contract_json).replace("__PAYLOAD_JSON__", payload_json).replace("__IMAGE_PAYLOAD_JSON__", image_payload_json).replace("__COMPILED_JSON__", compiled_json)


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
        compiled_payload = materialize_report_payload(
            raw_data,
            _BUILT_IN_CONTRACT,
            available_image_refs=image_refs.keys(),
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
            "payload_kind": detect_payload_kind(raw_data),
            "compiled_yaml": serialize_document(compiled_payload.to_dict(), fmt="yaml").strip(),
            "slide_count": len(compiled_payload.slides),
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
