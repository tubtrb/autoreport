param(
    [ValidateSet("smoke", "regression", "full")]
    [string]$Suite = "smoke",
    [string]$Session = "extai-chatgpt-spot",
    [ValidateSet("http", "local")]
    [string]$Mode = "http",
    [string]$OutputRoot = "output\verif_test",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [int]$SampleCount = 0,
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
        "tests\verif_test\cli.py"
        "--suite"
        $Suite
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
    if ($SampleCount -gt 0) {
        $cliArgs += @("--sample-count", "$SampleCount")
    }
    & $python @cliArgs
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $exitCode
