# ScopeWise consultant scan kit runner.
# Usage: .\scopewise-scan.ps1 <path-to-repo>
param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'   # vvaharness prints UTF-8 symbols; avoids cp1252 crashes on Windows consoles

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path (Join-Path $ScriptDir ".env"))) {
    Write-Error "Missing .env in $ScriptDir - create one with OPENAI_API_KEY (see README.md)."
    exit 1
}

if (-not (Get-Command vvaharness -ErrorAction SilentlyContinue)) {
    Write-Error "vvaharness is not on PATH - install it first (see README.md)."
    exit 1
}

Write-Host "== Estimating scan scope/cost (no spend yet) =="
vvaharness estimate --repo $RepoPath --config config.yaml

$reply = Read-Host "Continue with the scan? [y/N]"
if ($reply -notmatch '^[yY]$') {
    Write-Host "Aborted."
    exit 1
}

vvaharness scan --repo $RepoPath --stop-after s9 --config config.yaml

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
