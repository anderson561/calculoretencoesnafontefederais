@echo off
REM Abre a interface grafica da aplicacao. Duplo-clique para executar.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1"
