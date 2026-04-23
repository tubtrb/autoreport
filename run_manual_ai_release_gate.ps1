param(
    [string]$Session = "extai-chatgpt-spot",
    [ValidateSet("http", "local")]
    [string]$Mode = "http",
    [string]$OutputRoot = "output\verif_test",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$SessionCheckOnly
)

$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing virtualenv interpreter: $python"
}

$exitCode = 0
Push-Location $PSScriptRoot
try {
    $cliArgs = @(
        "tests\verif_test\release_gate_cli.py"
        "--session"
        $Session
        "--mode"
        $Mode
        "--output-root"
        $OutputRoot
        "--base-url"
        $BaseUrl
    )
    if ($SessionCheckOnly) {
        $cliArgs += "--session-check-only"
    }
    & $python @cliArgs
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $exitCode
