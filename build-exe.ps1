# Gera o executavel unico do Windows (.exe) com interface grafica.
# Requer as dependencias de desenvolvimento: setup.ps1 -Dev
# Uso: powershell -ExecutionPolicy Bypass -File build-exe.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pyi = ".\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyi)) {
    # Sem venv local (ex.: CI): usa o pyinstaller do PATH, se houver.
    $cmd = Get-Command pyinstaller -ErrorAction SilentlyContinue
    if ($cmd) {
        $pyi = $cmd.Source
    } else {
        Write-Host "PyInstaller nao encontrado. Rode primeiro: setup.ps1 -Dev" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Limpando builds anteriores..." -ForegroundColor Cyan
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

Write-Host "Gerando executavel (GUI, janela sem console)..." -ForegroundColor Cyan
& $pyi --onefile --windowed --name calculo-retencoes `
    --paths src `
    --collect-submodules retencoes `
    --collect-all numpy `
    --collect-all pandas `
    --collect-all openpyxl `
    --collect-all lxml `
    --collect-all reportlab `
    --distpath dist --workpath build\pyi --specpath build `
    src\gui.py

if (Test-Path "dist\calculo-retencoes.exe") {
    $mb = "{0:N1}" -f ((Get-Item "dist\calculo-retencoes.exe").Length / 1MB)
    Write-Host "OK: dist\calculo-retencoes.exe ($mb MB)" -ForegroundColor Green
} else {
    Write-Host "Falha: executavel nao foi gerado." -ForegroundColor Red
    exit 1
}
