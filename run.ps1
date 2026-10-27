# One-command setup + start on Windows:  .\run.ps1   (add -Yes to accept all installs, -Check to preview, -NoLlm for rule-based only)
param([switch]$Yes, [switch]$NoLlm, [switch]$Check, [switch]$NoBrowser, [int]$Port = 8501)
$python = $null
foreach ($candidate in @("python", "py")) {
    if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
    # the Microsoft Store "python" stub exists but is not Python: it answers with an install message and a non-zero code
    $version = & $candidate --version 2>&1
    if ($LASTEXITCODE -eq 0 -and "$version" -match "^Python 3") { $python = $candidate; break }
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
