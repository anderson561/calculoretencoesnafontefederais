# Cria o ambiente virtual local e instala as dependências.
# Uso: clique com o botao direito > "Executar com PowerShell", ou:
#   powershell -ExecutionPolicy Bypass -File setup.ps1
param(
    [switch]$Dev  # instala tambem as dependencias de desenvolvimento (testes/build)
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente virtual (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip

if ($Dev) {
    Write-Host "Instalando dependencias de desenvolvimento..." -ForegroundColor Cyan
    & $py -m pip install -r requirements-dev.txt
} else {
    Write-Host "Instalando dependencias de execucao..." -ForegroundColor Cyan
    & $py -m pip install -r requirements.txt
}

Write-Host "Ambiente pronto. Use run.ps1 para abrir a aplicacao." -ForegroundColor Green
