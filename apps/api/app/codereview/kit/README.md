# ScopeWise Code Security Review - scan kit

Scans your own repo on your own machine with your own OpenRouter key and
produces one zip that you upload to ScopeWise. Nothing leaves your machine
until you upload that zip. Needs Python 3.11+ (https://www.python.org/downloads/)
and an OpenRouter API key (https://openrouter.ai/keys).

**Do not `pip install` this zip** - it is not a Python package. Unzip it first.

## Quick start (3 commands)

Windows (PowerShell):

    cd scopewise-scan-kit
    .\setup.ps1                       # creates .venv, installs the scanner, asks for your key
    .\scopewise-scan.ps1 C:\path\to\repo

macOS / Linux:

    cd scopewise-scan-kit
    ./setup.sh
    ./scopewise-scan.sh /path/to/repo

If PowerShell refuses to run scripts, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry.

The scan script shows a scope/cost estimate first; nothing is spent until you
answer `y`. A small repo costs a few dollars and takes 30-120 minutes. It
writes `scopewise-scan-<repo>-<date>.zip` next to the scripts - upload that at
ScopeWise -> Code Security Review -> New review.

## Manual install (plain pip)

    pip install vendor/vvaharness-1.3.0-py3-none-any.whl

Then create `.env` in this folder (never share or commit it):

    OPENAI_API_KEY=<your OpenRouter key>
    OPENAI_BASE_URL=https://openrouter.ai/api/v1

and run the same `scopewise-scan` script - it uses `.venv` when present,
otherwise whatever `vvaharness` is on your PATH.

VVAH is Apache-2.0 (c) 2026 Visa, Inc. - see vendor/LICENSE and vendor/NOTICE.
