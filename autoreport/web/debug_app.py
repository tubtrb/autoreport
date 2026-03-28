"""Developer-facing debug app for Autoreport web flows."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from autoreport.template_flow import (
    get_built_in_contract,
    scaffold_payload,
    serialize_document,
)
from autoreport.web.app import (
    AI_DRAFT_PROMPT_YAML,
    compile_demo_payload,
    favicon,
    generate_demo_report,
    healthcheck,
)


_DEBUG_CONTRACT = get_built_in_contract()
_DEBUG_STARTER_AUTHORING = serialize_document(
    scaffold_payload(_DEBUG_CONTRACT, include_text_image=True).to_dict(),
    fmt="yaml",
).strip()
_DEBUG_CONTRACT_YAML = serialize_document(
    _DEBUG_CONTRACT.to_dict(),
    fmt="yaml",
).strip()

app = FastAPI(
    title="Autoreport Debug Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_debug_html() -> str:
    contract_json = json.dumps(_DEBUG_CONTRACT_YAML)
    starter_json = json.dumps(_DEBUG_STARTER_AUTHORING)
    draft_json = json.dumps(AI_DRAFT_PROMPT_YAML)
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Autoreport Debug Demo</title>
    <style>
      :root {
        --bg: #0f172a;
        --surface: #111c32;
        --panel: #0b1323;
        --text: #e2e8f0;
        --muted: #9fb0c8;
        --accent: #38bdf8;
        --border: #24334d;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at top right, rgba(56,189,248,0.12), transparent 22%), var(--bg);
        color: var(--text);
        font-family: "Segoe UI", Arial, sans-serif;
      }
      main { max-width: 1680px; margin: 0 auto; padding: 28px 20px 40px; }
      h1 { margin: 0 0 10px; color: var(--accent); }
      p { color: var(--muted); line-height: 1.6; }
      .layout { display: grid; grid-template-columns: 320px minmax(420px, 1.1fr) minmax(420px, 1.1fr); gap: 16px; align-items: start; }
      .card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 18px; }
      h2 { margin: 0 0 10px; font-size: 1rem; }
      textarea {
        width: 100%;
        min-height: 320px;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 14px;
        background: var(--panel);
        color: var(--text);
        font: 0.88rem/1.6 "Cascadia Mono", Consolas, monospace;
        resize: vertical;
      }
      .short { min-height: 210px; }
      .actions { display: grid; gap: 10px; margin-top: 14px; }
      .button-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
      button {
        border: none;
        border-radius: 12px;
        padding: 12px 14px;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
        background: #1d4ed8;
        color: white;
      }
      button.secondary { background: #1e293b; color: var(--text); border: 1px solid var(--border); }
      .status-errors, .status-hints, .upload-list { margin: 12px 0 0; padding-left: 18px; line-height: 1.6; }
      .status-errors { color: #fca5a5; }
      .status-hints { color: #86efac; }
      .upload-list { color: var(--muted); }
      @media (max-width: 1280px) {
        .layout { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Autoreport Debug Demo</h1>
      <p>
        This is a developer-facing surface. Use it to inspect the full template contract,
        normalize AI drafts into authoring payloads, inspect compiled runtime payloads,
        and verify uploads before generation.
      </p>
      <div class="layout">
        <section class="card">
          <h2>Debug Controls</h2>
          <p>Keep the user app simple. Use this page when you want to debug contract, normalization, or compilation behavior.</p>
          <div class="actions">
            <button id="load-draft" class="secondary" type="button">Load AI Draft Prompt</button>
            <button id="load-starter" class="secondary" type="button">Load Starter Authoring</button>
            <button id="compile" type="button">Compile / Normalize</button>
            <button id="generate" type="button">Generate PPTX</button>
          </div>
          <h2 style="margin-top: 18px;">Image Uploads</h2>
          <input id="image-files" type="file" multiple accept=".png,.jpg,.jpeg">
          <ul id="upload-list" class="upload-list"></ul>
          <h2 style="margin-top: 18px;">Status</h2>
          <div id="status-message">Ready.</div>
          <ul id="status-errors" class="status-errors"></ul>
          <ul id="status-hints" class="status-hints"></ul>
        </section>
        <section class="card">
          <h2>Input Draft</h2>
          <textarea id="payload-yaml" aria-label="Input draft"></textarea>
          <h2 style="margin-top: 18px;">Template Contract</h2>
          <textarea id="template-contract" class="short" readonly aria-label="Template contract"></textarea>
        </section>
        <section class="card">
          <h2>Normalized Authoring Payload</h2>
          <textarea id="normalized-yaml" class="short" readonly aria-label="Normalized authoring payload"></textarea>
          <h2 style="margin-top: 18px;">Compiled Report Payload</h2>
          <textarea id="compiled-yaml" class="short" readonly aria-label="Compiled report payload"></textarea>
        </section>
      </div>
    </main>
    <script>
      const CONTRACT_YAML = __CONTRACT_JSON__;
      const STARTER_AUTHORING = __STARTER_JSON__;
      const AI_DRAFT_PROMPT = __DRAFT_JSON__;

      const contractNode = document.getElementById("template-contract");
      const payloadNode = document.getElementById("payload-yaml");
      const normalizedNode = document.getElementById("normalized-yaml");
      const compiledNode = document.getElementById("compiled-yaml");
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

      function renderUploads() {
        uploadList.innerHTML = "";
        if (!uploadedRefs.length) {
          const li = document.createElement("li");
          li.textContent = "No uploaded files yet.";
          uploadList.appendChild(li);
          return;
        }
        for (const item of uploadedRefs) {
          const li = document.createElement("li");
          li.textContent = `${item.ref}: ${item.file.name}`;
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

      async function compilePayload() {
        setStatus("Compiling current payload...");
        const response = await postPayload("/api/compile");
        const payload = await response.json();
        if (!response.ok) {
          setStatus(payload.message || "Compilation failed.", payload.errors || [], payload.hints || []);
          return;
        }
        normalizedNode.value = payload.normalized_authoring_yaml || "";
        compiledNode.value = payload.compiled_yaml || "";
        setStatus(`Compile succeeded for ${payload.payload_kind}.`, [], payload.hints || []);
      }

      async function generatePayload() {
        setStatus("Generating debug PPTX...");
        const response = await postPayload("/api/generate");
        if (!response.ok) {
          const payload = await response.json();
          setStatus(payload.message || "Generation failed.", payload.errors || [], payload.hints || []);
          return;
        }
        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = downloadUrl;
        anchor.download = "autoreport_debug_demo.pptx";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(downloadUrl);
        setStatus("Generation succeeded. Download should begin shortly.");
      }

      contractNode.value = CONTRACT_YAML;
      payloadNode.value = AI_DRAFT_PROMPT;
      renderUploads();

      document.getElementById("load-draft").addEventListener("click", () => {
        payloadNode.value = AI_DRAFT_PROMPT;
        normalizedNode.value = "";
        compiledNode.value = "";
        setStatus("AI draft prompt loaded.");
      });
      document.getElementById("load-starter").addEventListener("click", () => {
        payloadNode.value = STARTER_AUTHORING;
        normalizedNode.value = STARTER_AUTHORING;
        compiledNode.value = "";
        setStatus("Starter authoring payload loaded.");
      });
      document.getElementById("compile").addEventListener("click", compilePayload);
      document.getElementById("generate").addEventListener("click", generatePayload);
      fileInput.addEventListener("change", () => {
        uploadedRefs = Array.from(fileInput.files || []).map((file, index) => ({
          ref: `image_${index + 1}`,
          file,
        }));
        renderUploads();
        setStatus(
          uploadedRefs.length ? "Uploads loaded." : "No uploads selected.",
          [],
          uploadedRefs.length ? [`Available refs: ${uploadedRefs.map((item) => item.ref).join(", ")}`] : []
        );
      });
    </script>
  </body>
</html>""".replace("__CONTRACT_JSON__", contract_json).replace("__STARTER_JSON__", starter_json).replace("__DRAFT_JSON__", draft_json)


DEBUG_INDEX_HTML = _render_debug_html()


@app.get("/", response_class=HTMLResponse)
def debug_page() -> HTMLResponse:
    return HTMLResponse(DEBUG_INDEX_HTML)


app.add_api_route("/healthz", healthcheck, methods=["GET"])
app.add_api_route("/favicon.ico", favicon, methods=["GET"])
app.add_api_route("/api/compile", compile_demo_payload, methods=["POST"])
app.add_api_route(
    "/api/generate",
    generate_demo_report,
    methods=["POST"],
    response_model=None,
)
