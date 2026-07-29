@echo off
REM Gera o executavel (.exe) com interface grafica. Duplo-clique para executar.
REM Requer dependencias de dev: rode antes "setup.bat dev".
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0build-exe.ps1"

echo.
pause
