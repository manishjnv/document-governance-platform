# ScopeSense consultant scan kit runner. Launched by scopewise-scan.cmd in the kit root.
# Usage: .\scopewise-scan.cmd <path-to-repo>
param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'   # vvaharness prints UTF-8 symbols; avoids cp1252 crashes on Windows consoles

$ScriptDir = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '..')).Path   # kit root
Set-Location $ScriptDir

if (-not (Test-Path (Join-Path $ScriptDir ".env"))) {
    Write-Error "Missing .env in $ScriptDir - run .\setup.cmd first (see README.md)."
    exit 1
}
if (-not (Test-Path $RepoPath)) {
    Write-Error "Repo path not found: $RepoPath"
    exit 1
}

# Prefer the kit's own .venv (created by setup); fall back to a PATH install.
if (Test-Path ".\.venv\Scripts\vvaharness.exe") {
    $Vva = ".\.venv\Scripts\vvaharness.exe"
} elseif (Get-Command vvaharness -ErrorAction SilentlyContinue) {
    $Vva = "vvaharness"
} else {
    Write-Error "Scanner not installed - run .\setup.cmd first (see README.md)."
    exit 1
}

# One transcript per run: logs\scan-<repo>-<timestamp>.log (kept locally, never uploaded).
$repoName = Split-Path -Leaf (Resolve-Path $RepoPath)
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Path "logs" -Force | Out-Null
$Log = Join-Path $ScriptDir "logs\scan-$repoName-$stamp.log"
# Native commands are run through cmd /c with 2>&1 merged THERE: under
# $ErrorActionPreference='Stop', PowerShell 5.1 would otherwise turn any stderr
# line (VVAH prints "[env] loaded" to stderr) into a terminating error.
function Run-Logged([string]$commandLine) {
    # (Tee-Object on PowerShell 5.1 writes UTF-16; write UTF-8 lines ourselves instead)
    & cmd /c "$commandLine 2>&1" | ForEach-Object { Write-Host $_; Add-Content -Path $Log -Value $_ -Encoding UTF8 }
    return $LASTEXITCODE   # only the code reaches the caller; output went to the console + log
}
function Mark([string]$msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH\:mm\:ss"), $msg
    Write-Host $line -ForegroundColor Cyan
    Add-Content -Path $Log -Value $line -Encoding UTF8
}
function Explain-Failure([string]$what, [int]$code) {
    Mark "$what FAILED (exit $code)"
    Write-Host ""
    Write-Host "  Where to look:" -ForegroundColor Yellow
    Write-Host "    transcript : $Log"
    $errs = Get-ChildItem (Join-Path $RepoPath "security-scan") -Filter "*_errors.jsonl" -ErrorAction SilentlyContinue
    if ($errs) { $errs | ForEach-Object { Write-Host "    traceback  : $($_.FullName)" } }
    $mf = Get-ChildItem -Path $ScriptDir -Filter "run_manifest_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($mf) { Write-Host "    stage timeline (per-stage start/end/outcome): $($mf.FullName)" }
    Write-Host "  Common causes: bad or unfunded OpenRouter key (401/402), no internet, repo path inside the kit folder." -ForegroundColor Gray
    exit $code
}

Mark "scan kit run started - repo=$RepoPath scanner=$Vva log=$Log"
Mark "estimate: started (no spend)"
$rc = Run-Logged "`"$Vva`" estimate --repo `"$RepoPath`" --config config.yaml"
if ($rc -ne 0) { Explain-Failure "estimate" $rc }
Mark "estimate: done"

# Size sanity check: a working folder with node_modules / .venv / build output
# reports hundreds of thousands of "code files" and would run for hours.
$estText = Get-Content $Log -Raw
$files = 0; $bytes = 0
if ($estText -match 'code files\s*:\s*([\d,]+)') { $files = [int]($Matches[1] -replace ',', '') }
if ($estText -match 'bytes\s*:\s*([\d,]+)') { $bytes = [long]($Matches[1] -replace ',', '') }
$junk = Get-ChildItem -Path $RepoPath -Directory -Recurse -Depth 3 -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @('node_modules', '.venv', 'venv', 'dist', 'build', '.next', '__pycache__', 'site-packages') } |
    Select-Object -First 3 -ExpandProperty FullName
if ($files -gt 20000 -or $bytes -gt 500MB) {
    Mark "refused: $files code files / $([math]::Round($bytes / 1MB)) MB - far too large to be source only"
    Write-Host ""
    Write-Host "  This folder is too large to be just source code ($files files, $([math]::Round($bytes / 1MB)) MB)." -ForegroundColor Red
    if ($junk) { Write-Host "  It contains dependency/build folders such as:" -ForegroundColor Yellow; $junk | ForEach-Object { Write-Host "    $_" } }
    Write-Host "  Scan a fresh clone instead (source only, no node_modules / .venv / build):" -ForegroundColor Yellow
    Write-Host "    git clone <repo-url-or-local-path> C:\scans\myrepo"
    Write-Host "    .\scopewise-scan.cmd C:\scans\myrepo"
    Write-Host "  Rule of thumb: ~60 files take about 100 minutes; 20,000+ files would take days." -ForegroundColor Gray
    exit 1
}
if ($files -gt 2000 -or $junk) {
    Write-Host ""
    Write-Host "  WARNING: $files code files" -ForegroundColor Yellow -NoNewline
    if ($junk) { Write-Host " and dependency/build folders present (e.g. $($junk[0]))" -ForegroundColor Yellow -NoNewline }
    Write-Host ". Expect a long run; a fresh git clone scans faster and cheaper." -ForegroundColor Yellow
}

$reply = Read-Host "Continue with the scan? [y/N]"
if ($reply -notmatch '^[yY]$') {
    Mark "aborted by user before scan"
    exit 1
}

Mark "scan: started (detection only, --stop-after s9) - progress lines below are also written to the log"
$rc = Run-Logged "`"$Vva`" scan --repo `"$RepoPath`" --stop-after s9 --config config.yaml"
if ($rc -ne 0) { Explain-Failure "scan" $rc }
Mark "scan: done"

$date = Get-Date -Format "yyyyMMdd"
$zipName = "scopewise-scan-$repoName-$date.zip"

$manifest = Get-ChildItem -Path $ScriptDir -Filter "run_manifest_*.json" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $manifest) { Explain-Failure "packaging (no run_manifest_*.json written)" 1 }
if (-not (Test-Path (Join-Path $RepoPath "security-scan\findings.json"))) { Explain-Failure "packaging (no security-scan\findings.json)" 1 }

$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $tmpDir | Out-Null
try {
    Copy-Item (Join-Path $RepoPath "security-scan\findings.json") $tmpDir
    Get-ChildItem (Join-Path $RepoPath "security-scan") -Filter "*.sarif" -ErrorAction SilentlyContinue |
        Copy-Item -Destination $tmpDir
    Copy-Item $manifest.FullName $tmpDir

    $zipPath = Join-Path $ScriptDir $zipName
    if (Test-Path $zipPath) { Remove-Item $zipPath }
    Compress-Archive -Path (Join-Path $tmpDir "*") -DestinationPath $zipPath
    Mark "packaged: $zipPath"

    Write-Host ""
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Green
    Write-Host "  |  Scan complete                                               |" -ForegroundColor Green
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Green
    Write-Host "  Results : $zipPath"
    Write-Host "  Log     : $Log"
    Write-Host "  Upload the zip at ScopeSense -> Code Security Review -> New review" -ForegroundColor Yellow
    Write-Host ""
} finally {
    Remove-Item -Recurse -Force $tmpDir
}
