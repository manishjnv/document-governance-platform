# ScopeWise scan kit - one-time setup (Windows). Launched by setup.cmd in the kit root.
# Creates .venv, installs the bundled scanner, asks for your OpenRouter key, writes .env.
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..')   # kit root

$Activity = 'ScopeWise scan kit setup'
$Interactive = [Environment]::UserInteractive -and -not [Console]::IsInputRedirected

function Show-Banner {
    Write-Host ''
    Write-Host '  ScopeWise Code Security Review - scan kit setup' -ForegroundColor Cyan
    Write-Host '  ------------------------------------------------' -ForegroundColor DarkCyan
    Write-Host '  Installs the bundled scanner into .venv in this folder and saves your key.' -ForegroundColor Gray
    Write-Host ''
}
function Step([int]$n, [string]$msg, [int]$pct) {
    Write-Progress -Activity $Activity -Status "Step $n of 4 - $msg" -PercentComplete $pct
    Write-Host ("  [{0}/4] {1}" -f $n, $msg) -ForegroundColor White
}
function Finish-Ok([string]$version) {
    Write-Progress -Activity $Activity -Completed
    Write-Host ''
    Write-Host '  +--------------------------------------------------------------+' -ForegroundColor Green
    Write-Host '  |  Setup complete                                              |' -ForegroundColor Green
    Write-Host ("  |  Scanner: {0,-51}|" -f $version) -ForegroundColor Green
    Write-Host '  |  Key saved to .env (never share or commit it)                |' -ForegroundColor Green
    Write-Host '  +--------------------------------------------------------------+' -ForegroundColor Green
    Write-Host ''
    Write-Host '  Next: scan a repository with' -ForegroundColor White
    Write-Host '        .\scopewise-scan.cmd C:\path\to\repo' -ForegroundColor Yellow
    Write-Host '  It shows a cost estimate first and asks before spending anything.' -ForegroundColor Gray
    Write-Host ''
    if ($Interactive) { Read-Host '  Press Enter to finish' | Out-Null }
}
function Finish-Fail([string]$msg) {
    Write-Progress -Activity $Activity -Completed
    Write-Host ''
    Write-Host "  SETUP FAILED: $msg" -ForegroundColor Red
    Write-Host '  Fix the problem above and run setup.cmd again. Help: README.md' -ForegroundColor Gray
    Write-Host ''
    if ($Interactive) { Read-Host '  Press Enter to close' | Out-Null }
    exit 1
}

Show-Banner

# 1. Python
Step 1 'Looking for Python 3.11 or newer' 5
$py = $null
foreach ($cand in @('py -3.12', 'py -3.11', 'python3', 'python')) {
    try {
        $v = & cmd /c "$cand -c ""import sys;print(sys.version_info[0]*100+sys.version_info[1])""" 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$v -ge 311) { $py = $cand; break }
    } catch {}
}
if (-not $py) { Finish-Fail 'Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH").' }
Write-Host "        found: $py" -ForegroundColor DarkGray

# 2. venv
Step 2 'Creating the private environment (.venv) - about 20 seconds' 15
& cmd /c "$py -m venv .venv"
if ($LASTEXITCODE -ne 0) { Finish-Fail 'Could not create .venv.' }
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --quiet --upgrade pip 2>$null | Out-Null

# 3. scanner + deps, with a live counter
$wheel = Get-ChildItem vendor -Filter 'vvaharness-*.whl' | Select-Object -First 1
Step 3 "Installing $($wheel.Name) and its dependencies - 1 to 3 minutes" 25
$count = 0
$failed = $false
& $python -m pip install --progress-bar off $wheel.FullName 2>&1 | ForEach-Object {
    $line = "$_"
    if ($line -match '^Collecting ') {
        $count++
        $pct = [Math]::Min(85, 25 + $count)
        Write-Progress -Activity $Activity -Status "Step 3 of 4 - resolving dependencies ($count packages so far)" -PercentComplete $pct
    } elseif ($line -match '^Installing collected packages') {
        Write-Progress -Activity $Activity -Status 'Step 3 of 4 - installing packages' -PercentComplete 90
        Write-Host "        installing $count packages..." -ForegroundColor DarkGray
    } elseif ($line -match '^Successfully installed') {
        Write-Host '        scanner installed' -ForegroundColor DarkGray
    } elseif ($line -match '^Requirement already satisfied: vvaharness') {
        Write-Host '        scanner already installed' -ForegroundColor DarkGray
    } elseif ($line -match '^ERROR') {
        $failed = $true
        Write-Host "        $line" -ForegroundColor Red
    }
}
if ($LASTEXITCODE -ne 0 -or $failed) { Finish-Fail 'Scanner install failed - see the ERROR lines above (usually no internet access).' }

# 4. key
Step 4 'Saving your OpenRouter API key' 95
if (Test-Path .env) {
    Write-Host '        .env already exists - keeping it' -ForegroundColor DarkGray
} else {
    if (-not $Interactive) { Finish-Fail 'No .env and no console to ask for the key. Create .env (see README.md) or run setup.cmd from a terminal.' }
    Write-Host '        Get a key at https://openrouter.ai/keys - input is hidden while you paste.' -ForegroundColor Gray
    $secure = Read-Host '        Paste your OpenRouter API key (starts with sk-or-)' -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    if (-not $plain) { Finish-Fail 'No key entered.' }
    "OPENAI_API_KEY=$plain`nOPENAI_BASE_URL=https://openrouter.ai/api/v1`n" | Set-Content -NoNewline -Encoding ascii .env
    Write-Host '        .env written' -ForegroundColor DarkGray
}

$version = (& .\.venv\Scripts\vvaharness.exe --version 2>&1 | Select-Object -Last 1)
Write-Progress -Activity $Activity -Status 'Done' -PercentComplete 100
Finish-Ok "$version"
