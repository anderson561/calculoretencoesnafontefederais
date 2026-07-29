@echo off
REM Instala o ambiente local. Duplo-clique para executar.
REM Use "setup.bat dev" para incluir dependencias de desenvolvimento (testes/build).
cd /d "%~dp0"

if /I "%~1"=="dev" (
    powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -Dev
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
)

echo.
pause
