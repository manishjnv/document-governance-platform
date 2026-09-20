#!/usr/bin/env bash
# ScopeSense scan kit - one-time setup (macOS / Linux). Run from the unzipped kit folder:
#   ./setup.sh
# Creates .venv, installs the bundled scanner, asks for your OpenRouter key, writes .env.
set -uo pipefail
export PYTHONUTF8=1
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -t 1 ]; then G=$'\e[32m'; R=$'\e[31m'; C=$'\e[36m'; Y=$'\e[33m'; D=$'\e[90m'; N=$'\e[0m'; else G=; R=; C=; Y=; D=; N=; fi
INTERACTIVE=0; [ -t 0 ] && INTERACTIVE=1

bar() {  # bar <pct> <label>
  local pct=$1 label=$2 width=30 filled hashes=""
  filled=$(( pct * width / 100 ))
  [ "$filled" -gt 0 ] && hashes=$(printf '#%.0s' $(seq 1 "$filled"))
  printf '\r  [%-*s] %3d%%  %s\033[K' "$width" "$hashes" "$pct" "$label"
}
step() { printf '\n  [%s/4] %s\n' "$1" "$2"; }
fail() {
  printf '\n\n  %sSETUP FAILED:%s %s\n  Fix the problem above and run ./setup.sh again. Help: README.md\n\n' "$R" "$N" "$1"
  [ "$INTERACTIVE" = 1 ] && read -r -p '  Press Enter to close' _
  exit 1
}

printf '\n  %sScopeSense Code Security Review - scan kit setup%s\n' "$C" "$N"
printf '  ------------------------------------------------\n'
printf '  %sInstalls the bundled scanner into .venv in this folder and saves your key.%s\n' "$D" "$N"

step 1 'Looking for Python 3.11 or newer'; bar 5 ''
PY=""
for cand in python3.12 python3.11 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$cand"; break
  fi
done
[ -n "$PY" ] || fail 'Python 3.11 or newer is required (https://www.python.org/downloads/).'
bar 10 "found: $PY"

step 2 'Creating the private environment (.venv) - about 20 seconds'; bar 15 ''
"$PY" -m venv .venv || fail 'Could not create .venv.'
.venv/bin/python -m pip install --quiet --upgrade pip >/dev/null 2>&1
bar 25 '.venv ready'

WHEEL="$(ls vendor/vvaharness-*.whl | head -n1)"
step 3 "Installing $(basename "$WHEEL") and its dependencies - 1 to 3 minutes"
count=0; failed=0
while IFS= read -r line; do
  case "$line" in
    Collecting*) count=$((count+1)); pct=$(( 25 + count )); [ "$pct" -gt 85 ] && pct=85; bar "$pct" "resolving dependencies ($count packages so far)";;
    "Installing collected packages"*) bar 90 "installing $count packages...";;
    "Successfully installed"*) bar 92 'scanner installed';;
    "Requirement already satisfied: vvaharness"*) bar 92 'scanner already installed';;
    ERROR*) failed=1; printf '\n  %s%s%s\n' "$R" "$line" "$N";;
  esac
done < <(.venv/bin/python -m pip install --progress-bar off "$WHEEL" 2>&1)
.venv/bin/python -c 'import vvaharness' 2>/dev/null || failed=1
[ "$failed" = 0 ] || fail 'Scanner install failed - see the ERROR lines above (usually no internet access).'

step 4 'Saving your OpenRouter API key'; bar 95 ''
if [ -f .env ]; then
  bar 97 '.env already exists - keeping it'
else
  [ "$INTERACTIVE" = 1 ] || fail 'No .env and no terminal to ask for the key. Create .env (see README.md).'
  printf '\n        Get a key at https://openrouter.ai/keys - input is hidden while you paste.\n'
  read -r -s -p '        Paste your OpenRouter API key (starts with sk-or-): ' KEY; echo
  [ -n "$KEY" ] || fail 'No key entered.'
  printf 'OPENAI_API_KEY=%s\nOPENAI_BASE_URL=https://openrouter.ai/api/v1\n' "$KEY" > .env
  chmod 600 .env
  bar 97 '.env written'
fi

VERSION="$(.venv/bin/vvaharness --version 2>&1 | tail -n1)"
bar 100 'done'; echo
printf '\n  %s+--------------------------------------------------------------+%s\n' "$G" "$N"
printf '  %s|  Setup complete                                              |%s\n' "$G" "$N"
printf '  %s|  Scanner: %-51s|%s\n' "$G" "$VERSION" "$N"
printf '  %s|  Key saved to .env (never share or commit it)                |%s\n' "$G" "$N"
printf '  %s+--------------------------------------------------------------+%s\n\n' "$G" "$N"
printf '  Next: scan a repository with\n        %s./scopewise-scan.sh /path/to/repo%s\n' "$Y" "$N"
printf '  %sIt shows a cost estimate first and asks before spending anything.%s\n\n' "$D" "$N"
[ "$INTERACTIVE" = 1 ] && read -r -p '  Press Enter to finish' _
exit 0
