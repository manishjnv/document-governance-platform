@echo off
rem ScopeWise scan kit - Windows launcher for scopewise-scan.ps1.
rem Usage: scopewise-scan.cmd C:\path\to\repo
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: scopewise-scan.cmd ^<path-to-repo^>
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -Path '.\bin\*.ps1' -ErrorAction SilentlyContinue; & '.\bin\scopewise-scan.ps1' -RepoPath '%~1'; exit $LASTEXITCODE"
