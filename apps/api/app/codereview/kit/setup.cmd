@echo off
rem ScopeWise scan kit - Windows launcher for setup.ps1 (works even when
rem PowerShell blocks downloaded scripts). Double-click or run from cmd/PowerShell.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -Path '.\bin\*.ps1' -ErrorAction SilentlyContinue; & '.\bin\setup.ps1'; exit $LASTEXITCODE"
