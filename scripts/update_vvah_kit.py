"""Keep the consultant scan kit on the latest VVAH release.

    python scripts/update_vvah_kit.py --check      # exit 0 up to date, 10 if a newer release exists
    python scripts/update_vvah_kit.py              # upgrade the kit to the latest release
    python scripts/update_vvah_kit.py --tag v1.4.0 # upgrade (or re-pin) to a given tag
    python scripts/update_vvah_kit.py --notes out.md  # also write the release's CHANGELOG section

Upgrade = build the wheel from the git tag (VVAH has no PyPI package or release
assets), vendor it with its LICENSE / NOTICE / THIRD_PARTY_LICENSES.md, and
rewrite every place the version is pinned: KIT_VERSION.json (+ sha256), the kit
README and config.yaml headers, and the web page constant. Run the kit tests
afterwards; .github/workflows/vvah-kit-update.yml does all of this weekly and
opens a PR. Stdlib only, so it runs in CI before any requirements install.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "visa/visa-vulnerability-agentic-harness"
ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "apps/api/app/codereview/kit"
VERSION_FILE = KIT / "bin/KIT_VERSION.json"
WEB_PAGE = ROOT / "apps/web/app/codereview/new/page.tsx"
VENDOR_DOCS = ("LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "scopesense-kit-updater"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def latest_tag() -> str:
    return json.loads(_get(f"https://api.github.com/repos/{REPO}/releases/latest"))["tag_name"]


def release_notes(tag: str) -> str:
    """The CHANGELOG section for this version (empty if the file has none)."""
    text = _get(f"https://raw.githubusercontent.com/{REPO}/{tag}/CHANGELOG.md").decode("utf-8")
    ver = tag.lstrip("v")
    m = re.search(rf"^## \[{re.escape(ver)}\].*?(?=^## \[|\Z)", text, re.M | re.S)
    return m.group(0).strip() if m else ""


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{path.relative_to(ROOT)}: expected '{old}' not found; update the pin by hand")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def upgrade(tag: str) -> None:
    current = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    old_ver, new_ver = current["vvah_version"], tag.lstrip("v")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--quiet", "--wheel-dir", tmp,
             f"git+https://github.com/{REPO}.git@{tag}"],
            check=True,
        )
        wheels = list(Path(tmp).glob("vvaharness-*.whl"))
        if len(wheels) != 1:
            raise SystemExit(f"expected one vvaharness wheel, got {wheels}")
        for old in (KIT / "vendor").glob("vvaharness-*.whl"):
            old.unlink()
        wheel = KIT / "vendor" / wheels[0].name
        shutil.copyfile(wheels[0], wheel)
    for name in VENDOR_DOCS:
        (KIT / "vendor" / name).write_bytes(_get(f"https://raw.githubusercontent.com/{REPO}/{tag}/{name}"))

    current.update(
        vvah_version=new_ver,
        vvah_tag=tag,
        wheel=f"vendor/{wheel.name}",
        wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        built=datetime.date.today().isoformat(),
        build_note=f"pip wheel --no-deps git+https://github.com/{REPO}.git@{tag} "
                   "(no PyPI release, no GitHub release assets)",
    )
    VERSION_FILE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8", newline="\n")
    if old_ver != new_ver:
        _replace(KIT / "README.md", f"vvaharness-{old_ver}-", f"vvaharness-{new_ver}-")
        _replace(KIT / "config.yaml", f"VVAH config profile, v{old_ver}.", f"VVAH config profile, v{new_ver}.")
        _replace(WEB_PAGE, f"const KIT_VERSION = '{old_ver}';", f"const KIT_VERSION = '{new_ver}';")
    print(f"kit: VVAH {old_ver} -> {new_ver} ({wheel.name}, sha256 {current['wheel_sha256'][:12]}...)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only; exit 10 if outdated")
    ap.add_argument("--tag", help="release tag to pin (default: latest release)")
    ap.add_argument("--notes", help="write the release's CHANGELOG section to this file")
    args = ap.parse_args()

    pinned = json.loads(VERSION_FILE.read_text(encoding="utf-8"))["vvah_tag"]
    tag = args.tag or latest_tag()
    print(f"pinned {pinned}, target {tag}")
    if args.notes:
        Path(args.notes).write_text(release_notes(tag) or f"No CHANGELOG entry for {tag}.", encoding="utf-8")
    if args.check:
        return 0 if tag == pinned else 10
    if tag == pinned and not args.tag:
        print("already up to date")
        return 0
    upgrade(tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
