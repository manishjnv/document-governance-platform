# ScopeWise scan kit - one-time setup (Windows). Run from the unzipped kit folder:
#   .\setup.ps1
# Creates .venv, installs the bundled scanner, asks for your OpenRouter key, writes .env.
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

$py = $null
foreach ($cand in @('py -3.12', 'py -3.11', 'python3', 'python')) {
    try {
        $v = & cmd /c "$cand -c ""import sys;print(sys.version_info[0]*100+sys.version_info[1])""" 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$v -ge 311) { $py = $cand; break }
    } catch {}
}
if (-not $py) {
    Write-Error "Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and re-run setup.ps1"
    exit 1
}

Write-Host "== Creating .venv with $py =="
& cmd /c "$py -m venv .venv"
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --quiet --upgrade pip
$wheel = Get-ChildItem vendor -Filter 'vvaharness-*.whl' | Select-Object -First 1
Write-Host "== Installing $($wheel.Name) (takes a minute) =="
& $python -m pip install --quiet $wheel.FullName

if (-not (Test-Path .env)) {
    $secure = Read-Host -AsSecureString "Paste your OpenRouter API key (starts with sk-or-, input hidden)"
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    if (-not $plain) {
        Write-Error "No key entered. Re-run setup.ps1 or create .env by hand (see README.md)."
        exit 1
    }
    "OPENAI_API_KEY=$plain`nOPENAI_BASE_URL=https://openrouter.ai/api/v1`n" | Set-Content -NoNewline -Encoding ascii .env
    Write-Host ".env written (never share or commit it)."
} else {
    Write-Host ".env already exists - keeping it."
}

& .\.venv\Scripts\vvaharness.exe --version
Write-Host ""
Write-Host "Setup done. Scan a repo with:"
Write-Host "  .\scopewise-scan.ps1 C:\path\to\repo"
