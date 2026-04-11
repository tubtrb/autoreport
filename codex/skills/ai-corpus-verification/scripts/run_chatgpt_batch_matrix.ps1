param(
    [string]$Session = "extai-chatgpt-spot",
    [int[]]$Counts = @(20, 30, 40, 50, 100),
    [string]$PromptPack = "codex\skills\ai-corpus-verification\references\chatgpt-product-full-prompt-pack.json",
    [string]$OutputRoot = "output\playwright",
    [string]$Collector = "codex\skills\ai-corpus-verification\scripts\collect_chatgpt_corpus.py",
    [string]$PromptExporter = "codex\skills\ai-corpus-verification\scripts\export_product_prompt_pack.py"
)

$ErrorActionPreference = "Stop"

& .\venv\Scripts\python.exe `
    $PromptExporter `
    --output-path $PromptPack

foreach ($count in $Counts) {
    $outputDir = Join-Path $OutputRoot ("chatgpt-pack-{0}" -f $count)
    if (Test-Path $outputDir) {
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $outputDir = Join-Path $OutputRoot ("chatgpt-pack-{0}-{1}" -f $count, $timestamp)
    }

    Write-Host ("Running ChatGPT batch count={0} -> {1}" -f $count, $outputDir)
    & .\venv\Scripts\python.exe `
        $Collector `
        --session $Session `
        --count $count `
        --prompt-pack $PromptPack `
        --output-dir $outputDir
}
