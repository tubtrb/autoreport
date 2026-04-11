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
    MANUAL_DRAFT_PROMPT_YAML,
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
_DEBUG_RECHECK_COMMAND = (
    r".\venv\Scripts\python.exe "
    r"codex\skills\manual-yaml-repair-proof\scripts\recheck_manual_corpus.py "
    r"--artifact-dir output\playwright\<artifact-folder>"
)
_DEBUG_SERVER_SMOKE_COMMAND = (
    r"powershell -File "
    r"codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 "
    r"-Session extai-chatgpt-spot -SmokeCount 1"
)
_DEBUG_SERVER_CORPUS_COMMAND = (
    r"powershell -File "
    r"codex\skills\manual-yaml-repair-proof\scripts\run_server_proof.ps1 "
    r"-Session extai-chatgpt-spot -SmokeCount 1 -CorpusCount 20"
)

app = FastAPI(
    title="Autoreport Debug Demo",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _render_debug_shell(
    *,
    page_title: str,
    intro: str,
    body_html: str,
    active_page: str,
    script_html: str = "",
) -> str:
    workspace_nav_class = (
        "debug-nav-link is-active" if active_page == "workspace" else "debug-nav-link"
    )
    proof_nav_class = (
        "debug-nav-link is-active" if active_page == "proof" else "debug-nav-link"
    )
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>__PAGE_TITLE__</title>
    <style>
      :root {
        --bg: #0f172a;
        --surface: #111c32;
        --panel: #0b1323;
        --text: #e2e8f0;
        --muted: #9fb0c8;
        --accent: #38bdf8;
        --accent-strong: #0ea5e9;
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
      h2 { margin: 0 0 10px; font-size: 1rem; }
      p { color: var(--muted); line-height: 1.6; }
      .hero-copy { max-width: 920px; margin: 0 0 18px; }
      .debug-nav {
        display: inline-flex;
        gap: 10px;
        margin-bottom: 18px;
        padding: 8px;
        background: rgba(11, 19, 35, 0.62);
        border: 1px solid var(--border);
        border-radius: 999px;
      }
      .debug-nav-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 10px 14px;
        border-radius: 999px;
        border: 1px solid transparent;
        color: var(--muted);
        text-decoration: none;
        font-weight: 700;
      }
      .debug-nav-link:hover { color: var(--text); border-color: rgba(159,176,200,0.2); }
      .debug-nav-link.is-active {
        background: rgba(14,165,233,0.14);
        border-color: rgba(56,189,248,0.38);
        color: var(--text);
      }
      .layout { display: grid; grid-template-columns: 320px minmax(420px, 1.1fr) minmax(420px, 1.1fr); gap: 16px; align-items: start; }
      .proof-layout { display: grid; grid-template-columns: minmax(360px, 0.8fr) minmax(420px, 1fr) minmax(420px, 1fr); gap: 16px; align-items: start; }
      .card { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; padding: 18px; min-width: 0; }
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
      .status-errors, .status-hints, .upload-list, .proof-list {
        margin: 12px 0 0;
        padding-left: 18px;
        line-height: 1.6;
      }
      .status-errors { color: #fca5a5; }
      .status-hints { color: #86efac; }
      .upload-list, .proof-list { color: var(--muted); }
      .command-box { min-height: 132px; }
      .proof-callout {
        margin-top: 16px;
        padding: 14px 16px;
        border-radius: 14px;
        background: rgba(14,165,233,0.08);
        border: 1px solid rgba(56,189,248,0.2);
      }
      .proof-grid { display: grid; gap: 16px; }
      .proof-stage {
        display: grid;
        gap: 12px;
        padding: 14px 16px;
        border-radius: 16px;
        background: rgba(11, 19, 35, 0.68);
        border: 1px solid rgba(36,51,77,0.9);
      }
      .proof-stage-label {
        display: inline-flex;
        width: fit-content;
        align-items: center;
        gap: 8px;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(14,165,233,0.16);
        color: var(--text);
        font-size: 0.82rem;
        font-weight: 700;
      }
      @media (max-width: 1280px) {
        .layout, .proof-layout { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <nav class="debug-nav" aria-label="Debug sections">
        <a href="/" class="__WORKSPACE_NAV_CLASS__">Debug Workspace</a>
        <a href="/proof" class="__PROOF_NAV_CLASS__">Repair Proof</a>
      </nav>
      <h1>__PAGE_TITLE__</h1>
      <p class="hero-copy">__INTRO__</p>
      __BODY_HTML__
    </main>
    __SCRIPT_HTML__
  </body>
</html>""".replace("__PAGE_TITLE__", page_title).replace("__INTRO__", intro).replace(
        "__BODY_HTML__", body_html
    ).replace("__SCRIPT_HTML__", script_html).replace(
        "__WORKSPACE_NAV_CLASS__", workspace_nav_class
    ).replace("__PROOF_NAV_CLASS__", proof_nav_class)


def _render_debug_workspace_html() -> str:
    contract_json = json.dumps(_DEBUG_CONTRACT_YAML)
    starter_json = json.dumps(_DEBUG_STARTER_AUTHORING)
    draft_json = json.dumps(MANUAL_DRAFT_PROMPT_YAML)
    body_html = """
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
"""
    script_html = """<script>
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
    </script>""".replace("__CONTRACT_JSON__", contract_json).replace(
        "__STARTER_JSON__", starter_json
    ).replace("__DRAFT_JSON__", draft_json)
    return _render_debug_shell(
        page_title="Autoreport Debug Demo",
        intro=(
            "This is a developer-facing surface. Use it to inspect the full template "
            "contract, normalize AI drafts into authoring payloads, inspect compiled "
            "runtime payloads, and verify uploads before generation."
        ),
        body_html=body_html,
        active_page="workspace",
        script_html=script_html,
    )


def _render_debug_proof_html() -> str:
    body_html = """
      <div class="proof-layout">
        <section class="card">
          <h2>Proof Runbook</h2>
          <p>
            Use this screen after manual YAML auto-repair, prompt transport, or local
            server restarts. Keep the main workspace focused on compile and generate
            inspection, and keep proof work here as a separate developer flow.
          </p>
          <div class="proof-grid">
            <div class="proof-stage">
              <span class="proof-stage-label">1. Code Proof</span>
              <ul class="proof-list">
                <li>Run `tests.test_web_app` and `tests.test_web_serve` first.</li>
                <li>Do not claim server proof when narrow tests are red.</li>
              </ul>
            </div>
            <div class="proof-stage">
              <span class="proof-stage-label">2. Saved Corpus Recheck</span>
              <ul class="proof-list">
                <li>Replay an existing ChatGPT artifact set through the current in-process repair path.</li>
                <li>This proves the new logic actually recovers historical failures.</li>
              </ul>
            </div>
            <div class="proof-stage">
              <span class="proof-stage-label">3. Restarted Server Proof</span>
              <ul class="proof-list">
                <li>Confirm `/healthz` on the restarted local server.</li>
                <li>Run at least one fresh ChatGPT HTTP smoke against `/api/manual-draft-check`.</li>
              </ul>
            </div>
          </div>
          <div class="proof-callout">
            Treat these as two distinct questions:
            code recovery against saved corpus, and live restarted-server behavior against a fresh conversation.
          </div>
        </section>
        <section class="card">
          <h2>Saved Corpus Recheck</h2>
          <p>Replay a saved artifact directory through the current manual YAML repair path.</p>
          <textarea class="command-box" readonly aria-label="Saved corpus recheck command">__RECHECK_COMMAND__</textarea>
          <h2 style="margin-top: 18px;">Live Server Smoke</h2>
          <p>Use the restarted local server and exercise the HTTP checker path end to end.</p>
          <textarea class="command-box" readonly aria-label="Live server smoke command">__SERVER_SMOKE_COMMAND__</textarea>
        </section>
        <section class="card">
          <h2>Stronger Live Proof</h2>
          <p>Use this when one smoke is not enough and you want a fresh live corpus sample set.</p>
          <textarea class="command-box" readonly aria-label="Stronger live proof command">__SERVER_CORPUS_COMMAND__</textarea>
          <h2 style="margin-top: 18px;">Expected Evidence</h2>
          <ul class="proof-list">
            <li>`recheck-summary.txt` from a saved real-provider artifact folder</li>
            <li>`summary.txt` from the fresh smoke or corpus output folder</li>
            <li>Warnings that show auto-repair was applied when the AI drift was indentation-only</li>
          </ul>
        </section>
      </div>
""".replace("__RECHECK_COMMAND__", _DEBUG_RECHECK_COMMAND).replace(
        "__SERVER_SMOKE_COMMAND__", _DEBUG_SERVER_SMOKE_COMMAND
    ).replace("__SERVER_CORPUS_COMMAND__", _DEBUG_SERVER_CORPUS_COMMAND)
    return _render_debug_shell(
        page_title="Autoreport Repair Proof",
        intro=(
            "Use this separate proof screen when you need to show that manual YAML "
            "recovery works against saved ChatGPT artifacts and against the restarted "
            "HTTP server path."
        ),
        body_html=body_html,
        active_page="proof",
    )


DEBUG_INDEX_HTML = _render_debug_workspace_html()
DEBUG_PROOF_HTML = _render_debug_proof_html()


@app.get("/", response_class=HTMLResponse)
def debug_page() -> HTMLResponse:
    return HTMLResponse(DEBUG_INDEX_HTML)


@app.get("/proof", response_class=HTMLResponse)
def debug_proof_page() -> HTMLResponse:
    return HTMLResponse(DEBUG_PROOF_HTML)


app.add_api_route("/healthz", healthcheck, methods=["GET"])
app.add_api_route("/favicon.ico", favicon, methods=["GET"])
app.add_api_route("/api/compile", compile_demo_payload, methods=["POST"])
app.add_api_route(
    "/api/generate",
    generate_demo_report,
    methods=["POST"],
    response_model=None,
)
