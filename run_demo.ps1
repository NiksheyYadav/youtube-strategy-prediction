param(
    [int]$Port = 8501
)

$python = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

& $python -m streamlit run (Join-Path $PSScriptRoot 'app.py') --server.address 127.0.0.1 --server.port $Port
