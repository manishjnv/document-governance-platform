# ScopeSense Code Security Review - scan kit

Scans your own repo on your own machine with your own OpenRouter key and
produces one zip that you upload to ScopeSense. Nothing leaves your machine
until you upload that zip. Needs Python 3.11+ (https://www.python.org/downloads/)
and an OpenRouter API key (https://openrouter.ai/keys).

**Do not `pip install` this zip** - it is not a Python package. Unzip it first.

## Quick start (3 commands)

Windows - double-click `setup.cmd`, or in a terminal:

    cd scopewise-scan-kit
    .\setup.cmd                       # creates .venv, installs the scanner, asks for your key
    .\scopewise-scan.cmd C:\path\to\repo

(`bin\` holds the PowerShell scripts the launchers run; you never need to
open it)

macOS / Linux:

    cd scopewise-scan-kit
    ./setup.sh
    ./scopewise-scan.sh /path/to/repo

**Scan a fresh clone, not your working folder.** The scanner reads every file
under the path, so `node_modules`, `.venv` or build output turn a 25k-line app
into a multi-hour, hundreds-of-dollars run. `git clone <url> C:\scans\myrepo`
then scan that. The script refuses folders over 20,000 files / 500 MB and warns
above 2,000 files. Timing: ~60 source files take about 100 minutes; there is a
10–15 minute floor even for tiny repos.

The scan script shows a scope/cost estimate first; nothing is spent until you
answer `y`. Every run writes a timestamped transcript to `logs/scan-<repo>-<time>.log`
(kept on your machine, never uploaded); if a stage fails the script prints the
transcript path, VVAH's `<repo>/security-scan/*_errors.jsonl` traceback and the
`run_manifest_*.json` stage timeline to look at. A small repo costs a few dollars and takes 30-120 minutes. It
writes `scopewise-scan-<repo>-<date>.zip` next to the scripts - upload that at
ScopeSense -> Code Security Review -> New review.

## Manual install (plain pip)

    pip install vendor/vvaharness-1.3.0-py3-none-any.whl

Then create `.env` in this folder (never share or commit it):

    OPENAI_API_KEY=<your OpenRouter key>
    OPENAI_BASE_URL=https://openrouter.ai/api/v1

and run the same `scopewise-scan` script - it uses `.venv` when present,
otherwise whatever `vvaharness` is on your PATH.

VVAH is Apache-2.0 (c) 2026 Visa, Inc. - see vendor/LICENSE and vendor/NOTICE.
