#!/usr/bin/env bash
# ScopeWise consultant scan kit runner.
# Usage: ./scopewise-scan.sh <path-to-repo>
set -uo pipefail
export PYTHONUTF8=1

if [ "${1:-}" = "" ]; then
  echo "Usage: scopewise-scan.sh <path-to-repo>" >&2
  exit 1
fi
REPO="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
  echo "Missing .env in $SCRIPT_DIR - run ./setup.sh first (see README.md)." >&2
  exit 1
fi
if [ ! -d "$REPO" ]; then
  echo "Repo path not found: $REPO" >&2
  exit 1
fi

# Prefer the kit's own .venv (created by setup.sh); fall back to a PATH install.
if [ -x ".venv/bin/vvaharness" ]; then
  VVA=".venv/bin/vvaharness"
elif command -v vvaharness >/dev/null 2>&1; then
  VVA="vvaharness"
else
  echo "Scanner not installed - run ./setup.sh first (see README.md)." >&2
  exit 1
fi

# One transcript per run: logs/scan-<repo>-<timestamp>.log (kept locally, never uploaded).
REPO_NAME="$(basename "$REPO")"
mkdir -p logs
LOG="$SCRIPT_DIR/logs/scan-${REPO_NAME}-$(date +%Y%m%d-%H%M%S).log"
mark() { local line; line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"; echo "$line"; echo "$line" >> "$LOG"; }
explain_failure() {  # explain_failure <what> <code>
  mark "$1 FAILED (exit $2)"
  echo
  echo "  Where to look:"
  echo "    transcript : $LOG"
  ls "$REPO"/security-scan/*_errors.jsonl 2>/dev/null | sed 's/^/    traceback  : /'
  MF="$(ls -t run_manifest_*.json 2>/dev/null | head -n1 || true)"
  [ -n "$MF" ] && echo "    stage timeline (per-stage start/end/outcome): $SCRIPT_DIR/$MF"
  echo "  Common causes: bad or unfunded OpenRouter key (401/402), no internet, repo path inside the kit folder."
  exit "$2"
}

mark "scan kit run started - repo=$REPO scanner=$VVA log=$LOG"
mark "estimate: started (no spend)"
"$VVA" estimate --repo "$REPO" --config config.yaml 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || explain_failure "estimate" "$rc"
mark "estimate: done"

# Size sanity check: a working folder with node_modules / .venv / build output
# reports hundreds of thousands of "code files" and would run for hours.
FILES=$(grep -E 'code files\s*:' "$LOG" | tail -n1 | sed 's/.*:\s*//; s/,//g'); FILES=${FILES:-0}
BYTES=$(grep -E '^\s*bytes\s*:' "$LOG" | tail -n1 | sed 's/.*:\s*//; s/,//g'); BYTES=${BYTES:-0}
JUNK=$(find "$REPO" -maxdepth 4 -type d \( -name node_modules -o -name .venv -o -name venv -o -name dist -o -name build -o -name .next -o -name __pycache__ -o -name site-packages \) 2>/dev/null | head -n3)
if [ "$FILES" -gt 20000 ] || [ "$BYTES" -gt 524288000 ]; then
  mark "refused: $FILES code files / $((BYTES / 1048576)) MB - far too large to be source only"
  echo
  echo "  This folder is too large to be just source code ($FILES files, $((BYTES / 1048576)) MB)."
  [ -n "$JUNK" ] && { echo "  It contains dependency/build folders such as:"; echo "$JUNK" | sed 's/^/    /'; }
  echo "  Scan a fresh clone instead (source only, no node_modules / .venv / build):"
  echo "    git clone <repo-url-or-local-path> ~/scans/myrepo"
  echo "    ./scopewise-scan.sh ~/scans/myrepo"
  echo "  Rule of thumb: ~60 files take about 100 minutes; 20,000+ files would take days."
  exit 1
fi
if [ "$FILES" -gt 2000 ] || [ -n "$JUNK" ]; then
  echo
  echo "  WARNING: $FILES code files${JUNK:+ and dependency/build folders present}. Expect a long run; a fresh git clone scans faster and cheaper."
fi

read -r -p "Continue with the scan? [y/N] " REPLY
case "$REPLY" in
  [yY]) ;;
  *) mark "aborted by user before scan"; exit 1 ;;
esac

mark "scan: started (detection only, --stop-after s9) - progress lines below are also written to the log"
"$VVA" scan --repo "$REPO" --stop-after s9 --config config.yaml 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || explain_failure "scan" "$rc"
mark "scan: done"

DATE="$(date -u +%Y%m%d)"
ZIP_NAME="scopewise-scan-${REPO_NAME}-${DATE}.zip"

MANIFEST="$(ls -t run_manifest_*.json 2>/dev/null | head -n1 || true)"
[ -n "$MANIFEST" ] || explain_failure "packaging (no run_manifest_*.json written)" 1
[ -f "$REPO/security-scan/findings.json" ] || explain_failure "packaging (no security-scan/findings.json)" 1

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cp "$REPO/security-scan/findings.json" "$TMP_DIR/"
cp "$REPO"/security-scan/*.sarif "$TMP_DIR/" 2>/dev/null || true
cp "$MANIFEST" "$TMP_DIR/"

rm -f "$ZIP_NAME"
if command -v zip >/dev/null 2>&1; then
  (cd "$TMP_DIR" && zip -q "$SCRIPT_DIR/$ZIP_NAME" ./*)
else
  python3 -m zipfile -c "$ZIP_NAME" "$TMP_DIR"/*
fi
mark "packaged: $SCRIPT_DIR/$ZIP_NAME"

echo
echo "  +--------------------------------------------------------------+"
echo "  |  Scan complete                                               |"
echo "  +--------------------------------------------------------------+"
echo "  Results : $SCRIPT_DIR/$ZIP_NAME"
echo "  Log     : $LOG"
echo "  Upload the zip at ScopeWise -> Code Security Review -> New review"
echo
