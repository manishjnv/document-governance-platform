#!/usr/bin/env bash
# ScopeWise consultant scan kit runner.
# Usage: scopewise-scan.sh <path-to-repo>
set -euo pipefail
export PYTHONUTF8=1

if [ "${1:-}" = "" ]; then
  echo "Usage: scopewise-scan.sh <path-to-repo>" >&2
  exit 1
fi
REPO="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
  echo "Missing .env in $SCRIPT_DIR — create one with OPENAI_API_KEY (see README.md)." >&2
  exit 1
fi

if ! command -v vvaharness >/dev/null 2>&1; then
  echo "vvaharness is not on PATH — install it first (see README.md)." >&2
  exit 1
fi

echo "== Estimating scan scope/cost (no spend yet) =="
vvaharness estimate --repo "$REPO" --config config.yaml

read -r -p "Continue with the scan? [y/N] " REPLY
case "$REPLY" in
  [yY]) ;;
  *) echo "Aborted."; exit 1 ;;
esac

vvaharness scan --repo "$REPO" --stop-after s9 --config config.yaml

REPO_NAME="$(basename "$REPO")"
DATE="$(date -u +%Y%m%d)"
ZIP_NAME="scopewise-scan-${REPO_NAME}-${DATE}.zip"

MANIFEST="$(ls -t run_manifest_*.json 2>/dev/null | head -n1 || true)"
if [ -z "$MANIFEST" ]; then
  echo "No run_manifest_*.json found in $SCRIPT_DIR — scan may have failed." >&2
  exit 1
fi

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

echo ""
echo "Created: $SCRIPT_DIR/$ZIP_NAME"
echo "Upload this file at ScopeWise -> Code Security Review -> New review"
