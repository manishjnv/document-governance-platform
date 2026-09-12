# ScopeWise consultant scan kit runner. Launched by scopewise-scan.cmd in the kit root.
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
    Write-Error "Missing .env in $ScriptDir - run .\setup.ps1 first (see README.md)."
    exit 1
}

# Prefer the kit's own .venv (created by setup.ps1); fall back to a PATH install.
if (Test-Path ".\.venv\Scripts\vvaharness.exe") {
    $Vva = ".\.venv\Scripts\vvaharness.exe"
} elseif (Get-Command vvaharness -ErrorAction SilentlyContinue) {
    $Vva = "vvaharness"
} else {
    Write-Error "Scanner not installed - run .\setup.ps1 first (see README.md)."
    exit 1
}

Write-Host "== Estimating scan scope/cost (no spend yet) =="
& $Vva estimate --repo $RepoPath --config config.yaml

$reply = Read-Host "Continue with the scan? [y/N]"
if ($reply -notmatch '^[yY]$') {
    Write-Host "Aborted."
    exit 1
}

& $Vva scan --repo $RepoPath --stop-after s9 --config config.yaml

$repoName = Split-Path -Leaf (Resolve-Path $RepoPath)
$date = Get-Date -Format "yyyyMMdd"
$zipName = "scopewise-scan-$repoName-$date.zip"

$manifest = Get-ChildItem -Path $ScriptDir -Filter "run_manifest_*.json" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $manifest) {
    Write-Error "No run_manifest_*.json found in $ScriptDir - scan may have failed."
    exit 1
}

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

    Write-Host ""
    Write-Host "Created: $zipPath"
    Write-Host "Upload this file at ScopeWise -> Code Security Review -> New review"
} finally {
    Remove-Item -Recurse -Force $tmpDir
}
