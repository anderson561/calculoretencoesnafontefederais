# Abre a interface grafica da aplicacao usando o ambiente virtual local.
# Uso: clique com o botao direito > "Executar com PowerShell", ou:
#   powershell -ExecutionPolicy Bypass -File run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Ambiente virtual nao encontrado. Rode primeiro: setup.ps1" -ForegroundColor Yellow
    exit 1
}

& $py src\gui.py
