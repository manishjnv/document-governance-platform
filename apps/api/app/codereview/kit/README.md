# ScopeWise Code Security Review — scan kit

Runs a security scan of your own repo on your own machine, using your own
OpenRouter key, and produces a zip you upload to ScopeWise. Nothing reaches
ScopeWise until you upload that zip.

Requires Python 3.11+ and an OpenRouter API key (https://openrouter.ai).

## Install

```
python -m venv .venv
.venv\Scripts\activate   # or: source .venv/bin/activate
pip install vendor/vvaharness-1.3.0-py3-none-any.whl
```

Create `.env` in this folder (never commit or share it):

```
OPENAI_API_KEY=<your OpenRouter key>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

## Run

```
./scopewise-scan.sh /path/to/repo        # macOS/Linux
.\scopewise-scan.ps1 C:\path\to\repo     # Windows
```

The scope/cost estimate prints first; nothing is spent until you confirm.
A typical small repo costs a few dollars. The script writes
`scopewise-scan-<repo>-<date>.zip` here — upload that at
ScopeWise -> Code Security Review -> New review.

## Attribution

VVAH is Apache-2.0 (c) 2026 Visa, Inc. — see vendor/LICENSE and vendor/NOTICE.
