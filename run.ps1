# One-command setup + start on Windows:  .\run.ps1   (add -Yes to accept all installs, -Check to preview, -NoLlm for rule-based only)
param([switch]$Yes, [switch]$NoLlm, [switch]$Check, [switch]$NoBrowser, [int]$Port = 8501)
$python = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $python = $candidate; break }
}
if (-not $python) {
    Write-Host "Python 3.10+ is required. Install it with:  winget install -e --id Python.Python.3.11" -ForegroundColor Yellow
    exit 1
}
$arguments = @((Join-Path $PSScriptRoot "scripts\launch.py"), "--port", $Port)
if ($Yes) { $arguments += "--yes" }
if ($NoLlm) { $arguments += "--no-llm" }
if ($Check) { $arguments += "--check" }
if ($NoBrowser) { $arguments += "--no-browser" }
& $python @arguments
exit $LASTEXITCODE
