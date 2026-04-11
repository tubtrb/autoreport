param(
    [string]$Session = "extai-chatgpt-spot",
    [int]$SmokeCount = 1,
    [int]$CorpusCount = 0,
    [string]$CheckerUrl = "http://127.0.0.1:8000/api/manual-draft-check"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
$python = Join-Path $repoRoot "venv\\Scripts\\python.exe"
$exportScript = Join-Path $repoRoot "codex\\skills\\ai-corpus-verification\\scripts\\export_product_prompt_pack.py"
$collectScript = Join-Path $repoRoot "codex\\skills\\ai-corpus-verification\\scripts\\collect_chatgpt_corpus.py"
$promptPack = Join-Path $repoRoot "codex\\skills\\ai-corpus-verification\\references\\chatgpt-product-full-prompt-pack.json"

Push-Location $repoRoot
try {
    & $python -m unittest tests.test_web_app tests.test_web_serve
    & $python $exportScript

    $healthzUrl = $CheckerUrl -replace "/api/manual-draft-check$", "/healthz"
    $healthz = Invoke-RestMethod -Uri $healthzUrl -Method Get
    if ($healthz.status -ne "ok") {
        throw "Health check did not return status=ok from $healthzUrl"
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $smokeDir = "output/playwright/manual-yaml-repair-proof-smoke-$timestamp"
    & $python $collectScript `
        --session $Session `
        --count $SmokeCount `
        --checker-mode http `
        --checker-url $CheckerUrl `
        --prompt-pack $promptPack `
        --output-dir $smokeDir

    Write-Output "__SMOKE_DIR__=$smokeDir"

    if ($CorpusCount -gt 0) {
        $corpusDir = "output/playwright/manual-yaml-repair-proof-corpus-$CorpusCount-$timestamp"
        & $python $collectScript `
            --session $Session `
            --count $CorpusCount `
            --checker-mode http `
            --checker-url $CheckerUrl `
            --prompt-pack $promptPack `
            --output-dir $corpusDir
        Write-Output "__CORPUS_DIR__=$corpusDir"
    }
}
finally {
    Pop-Location
}
