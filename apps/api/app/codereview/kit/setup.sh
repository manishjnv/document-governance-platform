#!/usr/bin/env bash
# ScopeWise scan kit - one-time setup (macOS / Linux). Run from the unzipped kit folder:
#   ./setup.sh
# Creates .venv, installs the bundled scanner, asks for your OpenRouter key, writes .env.
set -euo pipefail
export PYTHONUTF8=1
cd "$(dirname "${BASH_SOURCE[0]}")"

PY=""
for cand in python3.12 python3.11 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.11 or newer is required (https://www.python.org/downloads/)." >&2
  exit 1
fi

echo "== Creating .venv with $PY =="
"$PY" -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
WHEEL="$(ls vendor/vvaharness-*.whl | head -n1)"
echo "== Installing $(basename "$WHEEL") (takes a minute) =="
.venv/bin/python -m pip install --quiet "$WHEEL"

if [ ! -f .env ]; then
  read -r -s -p "Paste your OpenRouter API key (starts with sk-or-, input hidden): " KEY; echo
  if [ -z "$KEY" ]; then
    echo "No key entered. Re-run setup.sh or create .env by hand (see README.md)." >&2
    exit 1
  fi
  printf 'OPENAI_API_KEY=%s\nOPENAI_BASE_URL=https://openrouter.ai/api/v1\n' "$KEY" > .env
  chmod 600 .env
  echo ".env written (never share or commit it)."
else
  echo ".env already exists - keeping it."
fi

.venv/bin/vvaharness --version
echo
echo "Setup done. Scan a repo with:"
echo "  ./scopewise-scan.sh /path/to/repo"
